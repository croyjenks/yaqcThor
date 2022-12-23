import numpy as np
from time import sleep
from datetime import datetime
import WrightTools as wt

def monitor_power(pm, duration, num_samples=5, filepath=None, name=None):
    sample_duration = pm.get_conifg()['averaging']*0.01
    cycle_time = sample_duration*num_samples

    time, power_out = np.zeros(int(duration/cycle_time)+1), np.zeros(int(duration/cycle_time)+1)
    done = False
    for i in range(len(power_out)):
        if done:
            points_measured = i
            break
            
        if i==0:
            time[i] = 0
            start = datetime.now()
        else:
            time[i] = (datetime.now()-start).total_seconds()
        
        timer = 0
        pm.measure()
        while pm.busy():
            sleep(0.001)
            timer+=0.001
            if timer > cycle_time*10:
                print('power meter timed out, saving what was successfully measured')
                done = True
                break
        m = pm.get_measured()
        power_out[i] = m['power']

    time, power_out = time[:points_measured], power_out[:points_measured]
    start = f'{start}'
    if name is None:
        name = start.split('.')[0]
    
    out = wt.Data(name=name)
    out.create_variable('t', values=time, units='s')
    out['t'].attrs['label'] = "time (s)"
    out.create_channel('power', values=power_out, units='W')
    out['power'].attrs['label'] = "power (W)"
    out.attrs['meter averaging'] = pm.get_config()['averaging']
    out.attrs['start time'] = start
    out.transform('t')
    out.save(filepath=filepath)