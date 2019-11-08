# ups-utils
A set of utilities to monitor and react to the status of a supported UPS

## Getting Started
For any of the utilities to function, the config.py files must be customized using config.py.template as 
a template.

## ups-daemon
With no options specified, the utility will give the current status of the UPS configured in the config.py file.
With the *--daemon* option, *ups-daemon* will continuously check the status of the UPS.  When it detects that
the UPS is sourcing powering from the battery, it will check the amount of time it has been running on battery
and run the specified suspend script when the specified threshold is exceeded.  It will execute the specified
resume script when it detects power has resumed.  When the utility detects a Battery Low event from the UPS or
that time remaining for battery or the battery charge is below specified thresholds, then the shutdown script
will be executed. With the *--list* option, the utility will list all available SNMP commands for the configured
UPS.  The *--logfile filename* option is used to specify a logfile, but is not implemented at this time.

## ups-ls
This utility displays most relevant parameters for installed and compatible UPSs
listed in the config.json file.  By default, all available parameters are displayed.
The *--input* and *--output* options can be used to get relevant UPS input and output 
parameters.

## Under Development
The utility currently supports:
* APC UPS with AP9630 NMC 
* EATON UPS with PowerWalker NMC

It monitors the specified UPS using snmp v2c.  I have not implemented the ability to listen to snmp traps
yet, as I still have some research to do.  If you have different UPS and would like to extend the dictionary
in this [code](https://github.com/Ricks-Lab/ups-utils/blob/master/UPSmodules/UPSmodule.py) to support it, feel free to make a pull request.

## Reference Material
* [apc-ups-snmp](https://github.com/phillipsnick/apc-ups-snmp)
* [Partial List of OIDs for APC UPS](https://www.opsview.com/resources/monitoring/blog/monitoring-apc-ups-useful-oids)
* [Another Partial List of OIDs for APC UPS](https://www.itninja.com/blog/view/snmp-oids-for-apc-smart-ups-3000-rm-xl)
* [Another Partial List of OIDs for APC UPS](https://wiki.netxms.org/wiki/UPS_Monitoring_(APC)_via_SNMP)
* [APC Reference](https://www.apc.com/salestools/LFLG-AFACYW/LFLG-AFACYW_R1_EN.pdf)
* [snmp utilities](http://www.net-snmp.org/docs/man/)
* [MIB Browser](http://www.ireasoning.com/)
* [Eaton PowerWalker NMC](https://powerwalker.com/?page=nmc&lang=en)
