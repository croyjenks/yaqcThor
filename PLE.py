import numpy as np
from time import sleep
from datetime import date, datetime
import WrightTools as wt

objectives = {
    '5' : 0.893,
    '20' : 3.52,
    '100' : 18.2
}

def __waitfor(daemon, time_limit=-1):
    """
    Wait for a daemon while it's busy.
    Optionally return a flag is the daemon stays busy longer than a specified waiting time.

    Arguments
    ---------
    daemon : yaqc Client : The daemon to be waited on.
    time_limit : int, optional : The maximum allowable time to wait on the daemon. 
        If surpassed, the timeout flag is set to True, indicating an unexpected instrument timeout. 
        Default is -1, meaning wait indefinitely.

    Returns
    -------
    timed_out : bool, optional : Flag indicating an unexpected timeout of the instrument. 
        Only returned if time_limit is set to a positive value.
    """
    timed_out = False
    timer = 0

    while daemon.busy() and not timed_out:
        sleep(0.001)
        timer+=0.001
        if timer>time_limit:
            timed_out = True
    
    if time_limit>0:
        return timed_out

def PLE(opo, cam, start, stop, step, pm=None, pm_samples=5, name=None, filepath=None):
    """
    Measure a photoluminescence excitation spectrum using an OPO and an array detector. Optionally collect simultaneous data from a power meter during camera exposures.
    """
    if name is None:
        name = date.today()

    andor_config = cam.get_config()
    key = input("enter objective lens magnification: ")
    try:
        scale = objectives[key]
        units, unit_label = 'um', "(µm)"
    except KeyError:
        scale = 1
        units, unit_label = None, "pixel"

    wls = np.arange(*[start,stop].sort(), step=step)[:,None,None]
    x, y = np.arange(andor_config['aoi_width'])[None,:,None]*scale, np.arange(andor_config['aoi_height'])[None,None,:]*scale
    sig = np.zeros((x.size, y.size, wls.size))

    if pm is not None:
        pm_config = pm.get_config()
        sample_duration = pm.get_conifg()['averaging']*0.01
        cycle_time = sample_duration*pm_samples
        P = np.zeros((wls.size, (cam.get_exposure_time()/cycle_time)*10))
        t = np.zeros((wls.size, (cam.get_exposure_time()/cycle_time)*10))
        t_idx = np.zeros((cam.get_exposure_time()/cycle_time)*10)[None,:]
        t_max = 0
        if not pm.busy():
            pm_timeout = False

    if np.max(wl)>700 or np.min(wl)<420:
        raise ValueError("Scan range is beyond bounds of OPO. Valid wavelengths are from 420-700 nm.")

    print("shutter beam to measure dark counts")
    sleep(3)
    input("press enter when beam is shuttered ")
    cam.measure()
    if pm is not None:
        print("waiting 15 seconds for power meter to stabilize")
        sleep(15)
        pm.measure()
        pm_timeout = __waitfor(pm, time_limit=cycle_time)
        P_dark = pm.get_measured()
    __waitfor(cam)
    frame_dark = cam.get_measured()

    print("dark counts measured; unshutter the beam")
    sleep(3)
    input("press enter once beam is unshuttered ")

    for wl_idx, wl in enumerate(wls):
        opo.set_position(wl)
        __waitfor(opo)
        start_time = datetime.now()
        
        cam.measure()
        if pm is not None and not pm_timeout:
            i = 0
            while cam.busy():
                t[wl_idx,i] = (datetime.now()-start_time).total_seconds()
                pm.measure()
                pm_timeout = __waitfor(pm, time_limit=cycle_time)
                if not pm_timeout and i < t.size:
                    p = pm.get_measured()
                    P[wl_idx,i] = p['power']
                    i+=1
                else:
                    print(f"Power meter timed out while measuring data at wavelength {wl} - proceeding without power readings")
            if i>t_max:
                t_max=i
        else:
            __waitfor(cam)
        frame = cam.get_measured()
        sig[wl_idx,:,:] = frame['image']

    data = wt.Data(name=name)
    data.create_variable('wl', values=wls, units='nm')
    data.create_variable('x', values=x, units=units)
    data.create_variable('y', values=y, units=units)
    data['wl'].attrs['label'] = "excitation wavelength (nm)"
    data['x'].attrs['label'] = f'x {unit_label}'
    data['y'].attrs['label'] = f'y {unit_label}'
    data.create_channel('sig', values=sig)
    data['sig'].attrs['label'] = "sensor counts"

    data.attrs['dark counts'] = frame_dark
    data.attrs["exposure time"] = (cam.get_exposure_time(), 's')
    data.attrs["pixel readout rate"] = (cam.get_pixel_readout_rate(), 'Hz')
    data.attrs["shuttering mode"] = cam.get_electronic_shuttering_mode()
    data.attrs.update(andor_config)

    data.transform('wl','x','y')
    data.save(filepath=filepath)

    if pm is not None:
        filepath = f'{filepath.split(".")[0]}_power.wt5'
        t_idx, t, P = t_idx[None,:t_max], t[:,t_max].round(3), P[:,:t_max].round(3)
        power_data = wt.Data(name=f'{name}_power')
        power_data.create_variable('wl', values=wls[:,None], units='nm')
        power_data.create_variable('idx', values=t_idx)
        power_data['wl'].attrs['label'] = "excitation wavelength (nm)"
        power_data['idx'].attrs['label'] = "time point"
        power_data.create_channel('labtime', values=t, units='s')
        power_data.create_channel('power', values=P, units='W')
        power_data['labtime'].attrs['label'] = "exposure time (s)"
        power_data['power'].attrs['label'] = "power (W)"

        power_data.atrs['dark reading'] = P_dark['power']
        power_data.attrs.update(pm_config)

        power_data.transform('wl', 'idx')
        power_data.save(filepath=filepath)