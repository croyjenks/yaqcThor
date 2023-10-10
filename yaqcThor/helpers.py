__name__ = "helpers"
__author__ = "Chris R. Roy, Song Jin and John C. Wright Research Groups, Dept. of Chemistry, University of Wisconsin-Madison"
__version__ = '0.1.0'

"""
Tools to aid in the orchestration of experiments.
"""

import tomli
from time import sleep
import numpy as np

def get_config_values(daemon):
    """
    Get a daemon's configuration as a dictionary by parsing it as a TOML string.

    Argumens
    --------
    daemon : yaqc.Client - The daemon to retrieve the configuration of.

    Returns
    -------
    values : dict or None - The configuration. Returns None if the string could not be parsed as TOML code.
    """
    config = daemon.get_config()
    #passthrough if it's already a dictionary
    if isinstance(config, dict):
        return config

    elif isinstance(config, str):    
        try:
            values = tomli.loads(config)
            return values
        except tomli.TOMLDecodeError:
            print(f"Unable to retrieve configuration values for daemon {daemon.name}.")
            return None

def prompt_for_action(prompt_message, proceed_prompt=None, wait_time_s=3) -> None:
    """
    Prompt the user to perform an action in the lab. Wait for user input to proceed.

    Arguments
    ---------
    prompt_message : str - Message to request action from the user.
    proceed_prompt : str (optional) - Prompt to incite user input when the action is complete.
        Default is None, which defaults to the prompt "Press enter to proceed: ".
    wait_time_s : int (optional) - The amount of time to wait before prompting the user to proceed. Default is 3 seconds.

    Returns
    -------
    None - Terminates when user provides input to proceed.
    """

    default_proceed_prompt = "Press enter to proceed: "
    if proceed_prompt is None:
        proceed_prompt = default_proceed_prompt

    print(prompt_message)
    sleep(wait_time_s)
    input(proceed_prompt)

def prompt_for_value(prompt_message, valid_inputs, ignore_invalid_input=True) -> str or None:
    """
    Prompt the user to enter a value.
    Optionally, ask continuously if it does not match a set of specified valid inputs.

    Arguments
    ---------
    prompt_message : str - The message to display to the user.
    valid_inputs : set of str and/or numbers; list of numbers; or None - The entries to accept. Default is None.
        A set of items specifies exact entries to accept, including numerical entries.
        A list of numbers specifies a range within which an entry is valid.
    ignore_invalid_input : bool (optional) - Option to proceed if the user enters an invalid input.
        If True, the function will return None user input is invalid.

    Returns
    -------
    value : str or None - The value from user input, or None if an invalid input was ignored.
    """

    input_is_number = False
    if isinstance(valid_inputs, list) or isinstance(valid_inputs, tuple):
        valid_inputs = np.asarray(valid_inputs)
        valid_inputs = (np.min(valid_inputs), np.max(valid_inputs))
        input_is_number = True
    elif isinstance(valid_inputs, set):
        valid_inputs = {str(valid_input) for valid_input in valid_inputs}
    else:
        raise TypeError(f"valid_inputs must be a set or a list of numbers, not {type(valid_inputs)}")

    input_accepted = False
    while not input_accepted:
        user_input = input(prompt_message)
        feedback_message = None

        if valid_inputs is None:
            value = user_input
            input_accepted = True
        else:
            if input_is_number:
                if not user_input.isdigit():
                    feedback_message = "Numerical input required."
                elif float(user_input)<valid_inputs[0] or float(user_input)>valid_inputs[1]:
                    feedback_message = f"Input fell outside allowed range. Input must be between {valid_inputs[0]} and {valid_inputs[1]}"
                else:
                    value = user_input
                    input_accepted = True
            else:
                if user_input not in valid_inputs:
                    feedback_message = f"Input not valid. Accepted inputs: <{valid_inputs}>"
                else:
                    value = user_input
                    input_accepted = True

        if not input_accepted:
            if ignore_invalid_input:
                value = None
                input_accepted = True
            else:
                print(feedback_message)

    return value

def waitfor(daemon, time_limit_s=-1) -> bool or None:
    """
    Wait for a daemon while it's busy.
    Optionally return a flag if the daemon stays busy longer than a specified waiting time.

    Arguments
    ---------
    daemon : yaqc Client - The daemon to wait for.
    time_limit_s : int (optional) - The maximum allowable time to wait on the daemon, in seconds. 
        If surpassed, the timeout flag is set to True, indicating an unexpected instrument timeout. 
        Default is -1, meaning wait indefinitely.

    Returns
    -------
    timed_out : bool (optional) - Flag indicating an unexpected timeout of the instrument. 
        Only returned if time_limit_s is set to a positive value.
    """
    timed_out = False
    timer = 0

    while daemon.busy() and not timed_out:
        sleep(0.001)
        timer+=0.001
        if time_limit_s>0 and timer>time_limit_s:
            timed_out = True
    
    if time_limit_s>0:
        return timed_out