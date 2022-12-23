import numpy as np
from time import sleep
from datetime import date
import WrightTools as wt

def tuning_curve(opo, pm, start, stop, step, samples=100, filepath=None):
    #terminate preemptively is scan parameters are invalid
    args = sorted([start, stop])+[step]
    opo_wavelengths = np.arange(*args)
    if np.min(opo_wavelengths)<400 or np.max(opo_wavelengths)>700:
        return ValueError('the specified excitation range is extends beyond the capacity of the instrument, excitation range must be from 400-700 nm')

    #get dark counts
    print('turn laser off to collect dark count sample')
    sleep(2)
    input('press enter once laser is off ')
    print('measuring dark counts')

    p = np.zeros(samples)
    timer = 0
    for i in range(samples):
        pm.measure()
        while pm.busy():
            sleep(0.005)
            timer += 0.005
            if timer > 0.1*samples:
                print('power meter timeout error, aborting acquisition')
                return
        m = pm.get_measured()
        p[i] = m['power']
    k = (np.average(p), np.std(p))
    
    #collect excitation spectrum
    print('turn on the laser')
    sleep(2)
    input('press enter once laser is on ')
    print('waiting 5 seconds for laser to stabilize')
    sleep(5)
    print('measuring OPO power curve')

    power_out, std_out = np.zeros(opo_wavelengths.size), np.zeros(opo_wavelengths.size)
    for i, wl in enumerate(opo_wavelengths):
        opo.set_position(wl)
        while opo.busy():
            sleep(0.1)
        sleep(1)
        ptemp = np.zeros(1000)
        time_busy = 0
        for j in range(1000):
            pm.measure()
            while pm.busy():
                sleep(0.005)
                time_busy += 0.005
                if time_busy > 60:
                    print(f'power meter timeout error, acquisition aborted at {wl} nm')
                    out = wt.Data(name=f'OPO_{date.today()}')
                    out.create_variable('wl', values=opo_wavelengths[:i], units='nm')
                    out.create_channel('power', values=power_out[:i])
                    out.create_channel('std', values=std_out[:i])
                    out.transform('wl')
                    out.attrs['dark reading'] = k
                    out.save(filepath=filepath)
            m = pm.get_measured()
            ptemp[j] = m['power']
        power_out[i] = np.average(ptemp)
        std_out[i] = np.std(ptemp)
        print(f'{round(1000*wl, 3)} nm, {power_out[i]} +/- {round(1000*std_out[i], 3)} mW')

    out = wt.Data(name=f'OPO_{date.today}')
    out.create_variable('wl', values=opo_wavelengths, units='nm')
    out['wl'].attrs['label'] = "excitation wavelength (nm)"
    out.create_channel('power', values=power_out)
    out['power'].attrs['label'] = "OPO power (W)"
    out.create_channel('std', values=std_out)
    out['std'].attrs['label'] = "σ (W)"
    out.transform('wl')
    out.attrs['dark reading'] = k
    out.save(filepath=filepath)