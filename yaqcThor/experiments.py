__name__ = "experiments"
__author__ = "Chris R. Roy, Song Jin and John C. Wright Research Groups, Dept. of Chemistry, University of Wisconsin-Madison"
__version__ = '0.1.0'

"""
Predefined experiment scripts for the PL microscope.
"""

import numpy as np
from time import sleep
from datetime import date, datetime
import WrightTools as wt
from helpers import waitfor, prompt_for_action, prompt_for_value
import constants

def monitor_power(pm, duration, pm_samples=5, filepath=None, name=None):
    """
    Record readings from a power meter for a specified duration of time.

    Arguments
    ---------
    pm : yaqc.Client - Daemon for the power meter.

    duration : int - The duration of the measurment in seconds.
    pm_samples : int (optional) - The number of power readings to average into a single data point. Default is 5.

    filepath : str (optional) - The file path to which the data is saved. Default is None.
    name : str (optional) - The name of the data. Default is None.

    Returns
    -------
    None - Generates a WrightTools Data object for the measurement and saves it to the specified file path.
    """
    sample_duration = pm.get_conifg()['averaging']*0.01
    cycle_time = sample_duration*pm_samples

    time, power_out = np.zeros(int(duration/cycle_time)+1), np.zeros(int(duration/cycle_time)+1)
    measurement_completed = False

    for i in range(len(power_out)):
        if measurement_completed:
            points_measured = i
            break
            
        if i==0:
            time[i] = 0
            start = datetime.now()
        else:
            time[i] = (datetime.now()-start).total_seconds()
        
        pm.measure()
        timed_out = waitfor(pm, time_limit_s = cycle_time*10)
        if timed_out:
            print('power meter timed out, saving what was successfully measured')
            measurement_completed = True
        else:
            m = pm.get_measured()
            power_out[i] = m['power']

    time, power_out = time[:points_measured], power_out[:points_measured]
    start = str(start)
    if name is None:
        name = f'power-reading_{start.split(".")[0]}'
    
    out = wt.Data(name=name)
    out.create_variable('t', values=time, units='s')
    out['t'].attrs['label'] = "time (s)"
    out.create_channel('power', values=power_out, units='W')
    out['power'].attrs['label'] = "power (W)"
    out.attrs['meter averaging'] = pm.get_config()['averaging']
    out.attrs['start time'] = start
    out.transform('t')
    out.save(filepath=filepath)

def PLE_spectrum(opo, camera, start, stop, step, 
        pm=None, pm_samples=5, name=None, filepath=None):
    """
    Measure a photoluminescence excitation spectrum using an OPO and an array detector. 
    Optionally collect simultaneous data from a power meter during exposures.

    Arguments
    ---------
    opo : yaqc.Client - Daemon for the OPO.
    camera : yaqc.Client - Daemon for the array detector.

    start : int - Start wavelength of the scan.
    stop : int - End wavelength of the scan.
    step : int - Scan increment.

    pm : yaqc.Client (optional) - Daemon for the power meter. Default is None.
    pm_samples : int (optional) - Number of power readings to average into a single data point. Default is 5.

    name : str (optional) - Name of the dataset. Default is None.
    filepath : str (optional) - File path to save the data to. Default is None.
    
    Returns
    -------
    None - Generates a WrightTools Data instance for the PLE spectrum and the power readings. 
        Saves each to the specified directory.
    """
    #get camera configuration
    andor_config = camera.get_config()

    #get microscope configuration with help from user
    magnification = prompt_for_value("Enter objective lens magnification: ",
                        {mag for mag in constants.OBJECTIVE_CALIBRATION_SCALES.keys()})
    if magnification is not None:
        scale = constants.OBJECTIVE_CALIBRATION_SCALES[magnification]
        units, unit_label = 'um', "(µm)"
    else:
        scale = 1
        units, unit_label = None, "pixel"

    #get power meter configuration and check for timeout (if in use)
    if pm is not None:
        pm_config = pm.get_config()
        sample_duration = pm_config()['averaging']*0.01
        cycle_time = sample_duration*pm_samples
        P = np.zeros((wls.size, (camera.get_exposure_time()/cycle_time)*10))
        t = np.zeros((wls.size, (camera.get_exposure_time()/cycle_time)*10))
        t_idx = np.zeros((camera.get_exposure_time()/cycle_time)*10)[None,:]
        t_max = 0
        if not pm.busy():
            pm_timeout = False

    #define measurement parameters
    wls = np.arange(*[start,stop].sort(), step=step)[:,None,None]
    if np.min(wls)<420 or np.max(wls)<700:
        raise ValueError("Scan range is beyond bounds of the OPO. Valid wavelengths are from 420-700 nm.")
    x, y = np.arange(andor_config['aoi_width'])[None,:,None]*scale, np.arange(andor_config['aoi_height'])[None,None,:]*scale
    sig = np.zeros((x.size, y.size, wls.size))

    #measure dark counts with help from user
    prompt_for_action("Shutter beam to measure dark counts")
    camera.measure()
    if pm is not None:
        print("Waiting 15 seconds for power meter to stabilize")
        sleep(15)
        pm.measure()
        pm_timeout = waitfor(pm, time_limit_s=cycle_time)
        P_dark = pm.get_measured()
    waitfor(camera)
    frame_dark = camera.get_measured()
    prompt_for_action("Unshutter the beam")

    #measure a PLE spectrum with power readings in tandem
    print("Measuring excitation spectrum...")
    for wl_idx, wl in enumerate(wls):
        #reposiiton OPO and begin acquiring next data point
        opo.set_position(wl)
        waitfor(opo)
        camera.measure()
        exposure_start_time = datetime.now()

        #optionally measure power, skip if power meter is timed out
        if pm is not None and not pm_timeout:
            i = 0
            while camera.busy():
                t[wl_idx,i] = (datetime.now()-exposure_start_time).total_seconds()
                pm.measure()
                pm_timeout = waitfor(pm, time_limit_s=cycle_time)
                if not pm_timeout and i < t.size:
                    p = pm.get_measured()
                    P[wl_idx,i] = p['power']
                    i+=1
                else:
                    print(f"Power meter timed out while measuring data at wavelength {wl} - proceeding without power readings")
            if i>t_max:
                t_max=i
        else:
            waitfor(camera)

        #store exposure in array
        frame = camera.get_measured()
        sig[wl_idx,:,:] = frame['image']

    #set name for data
    if name is None:
        spectrum_name = f'PLE-raw-images_{date.today()}'
        power_name = f'PLE-power-readings_{date.today()}'

    data = wt.Data(name=spectrum_name)
    data.create_variable('wl', values=wls, units='nm')
    data.create_variable('x', values=x, units=units)
    data.create_variable('y', values=y, units=units)
    data['wl'].attrs['label'] = "excitation wavelength (nm)"
    data['x'].attrs['label'] = f'x {unit_label}'
    data['y'].attrs['label'] = f'y {unit_label}'
    data.create_channel('sig', values=sig)
    data['sig'].attrs['label'] = "sensor counts"

    data.attrs['dark counts'] = frame_dark
    data.attrs["exposure time"] = (camera.get_exposure_time(), 's')
    data.attrs["pixel readout rate"] = (camera.get_pixel_readout_rate(), 'Hz')
    data.attrs["shuttering mode"] = camera.get_electronic_shuttering_mode()
    data.attrs.update(andor_config)

    data.transform('wl','x','y')
    data.save(filepath=filepath)

    if pm is not None:
        filepath = f'{filepath.split(".")[0]}_power.wt5'
        t_idx, t, P = t_idx[None,:t_max], t[:,t_max].round(3), P[:,:t_max].round(3)
        power_data = wt.Data(name=power_name)
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

def tuning_curve(opo, pm, start, stop, step, pm_samples=100, name=None, filepath=None):
    """
    Measure an OPO tuning curve with a power meter.

    Arguments
    ---------
    opo : yaqc.Client - Daemon for the OPO.
    pm : yaqc.Client - Daemon for the power meter.
    start : int

    start : int - Start wavelength of the scan.
    stop : int - End wavelength of the scan.
    step : int - Scan increment.

    pm_samples : int (optional) - The number of power readings to average into a single data point. Default is 100.

    name : str (optional) - Name of the dataset. Default is None.
    filepath : str (optional) - The file path to which the data is saved. Default is None.

    Returns
    -------
    None - Generates a WrightTools Data object for the measurements and saves it to the specified file path.
    """
    #get power meter configuration and check for timeout
    if pm is not None:
        pm_config = pm.get_config()
        sample_duration = pm_config['averaging']*0.01
        cycle_time = sample_duration*pm_samples
        if not pm.busy():
            pm_timeout = False
        else:
            print('Power meter timed out; aborting acquisition.')
            return        

    #define measurement parameters
    wls = np.arange(*[start,stop].sort(), step=step)
    if np.min(wls)<420 or np.max(wls)<700:
        raise ValueError("Scan range is beyond bounds of the OPO. Valid wavelengths are from 420-700 nm.")

    #get dark counts
    prompt_for_action("Shutter beam to measure dark counts")
    print("Measuring dark counts")
    p = np.zeros(pm_samples)
    for i in range(pm_samples):
        pm.measure()
        pm_timeout = waitfor(pm, time_limit_s=cycle_time*2)
        if pm_timeout:
            print('Power meter timed out; aborting acquisition.')
            return     
        m = pm.get_measured()
        p[i] = m['power']
    k = (np.average(p), np.std(p))
    prompt_for_action("Unshutter the beam")

    #collect excitation spectrum
    print("Measuring OPO tuning curve...")
    power_out, std_out = np.zeros(wls.size), np.zeros(wls.size)
    for i, wl in enumerate(wls):
        if pm_timeout:
            print(f"Power meter timed out at wavelength {wl}. Saving existing data points.")
            points_measured = i
            break

        opo.set_position(wl)
        waitfor(opo)

        p = np.zeros(pm_samples)
        for j in range(pm_samples):
            pm.measure()
            pm_timeout = waitfor(pm, time_limit_s=cycle_time*2)
            if pm_timeout:
                break
            else:
                m = pm.get_measured()
                p[j] = m['power']

        power_out[i] = np.average(p)
        std_out[i] = np.std(p)

    if pm_timeout:
        power_out = power_out[:points_measured]
        std_out = std_out[:points_measured]

    if name is None:
        name = f'OPO-tuning-curve_{date.today}'

    out = wt.Data(name=name)
    out.create_variable('wl', values=wls, units='nm')
    out['wl'].attrs['label'] = "excitation wavelength (nm)"
    out.create_channel('power', values=power_out)
    out['power'].attrs['label'] = "OPO power (W)"
    out.create_channel('std', values=std_out)
    out['std'].attrs['label'] = "σ (W)"
    out.transform('wl')
    out.attrs['dark reading'] = k
    out.save(filepath=filepath)