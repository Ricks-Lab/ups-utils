![](https://img.shields.io/github/license/Ricks-Lab/ups-utils)
![GitHub commit activity](https://img.shields.io/github/commit-activity/y/Ricks-Lab/ups-utils)
![GitHub last commit](https://img.shields.io/github/last-commit/Ricks-Lab/ups-utils)
![Libraries.io SourceRank](https://img.shields.io/librariesio/sourcerank/pypi/rickslab-ups-utils)

# rickslab-ups-utils

A set of utilities to monitor and react to the status of a set of supported UPSs.

## Installation

There are currently 3 possible ways of installing *rickslab-ups-utils* as summarized here:

* [Repository](https://github.com/Ricks-Lab/ups-utils/blob/master/docs/USER_GUIDE.md#repository-installation) -
You can always clone the repository and run that version. This is useful if you want to contribute to the project.

  ![Custom badge](https://img.shields.io/endpoint?color=%23417B5D&url=https%3A%2F%2Frickslab.com%2Fbadges%2Fgh_ups_version.json)
* [PyPI](https://github.com/Ricks-Lab/ups-utils/blob/master/docs/USER_GUIDE.md#pypi-installation) -
Meant for users wanting to run the very latest version.  All **PATCH** level versions are released
here first.  This installation method is also meant for users not on a Debian distribution.

  [![PyPI version](https://badge.fury.io/py/rickslab-ups-utils.svg)](https://badge.fury.io/py/rickslab-ups-utils)
  [![Downloads](https://pepy.tech/badge/rickslab-ups-utils)](https://pepy.tech/project/rickslab-ups-utils)
* [Rickslab.com Debian](https://github.com/Ricks-Lab/ups-utils/blob/master/docs/USER_GUIDE.md#rickslabcom-debian-installation) -
  Lags the PyPI release in order to assure robustness. May not include every **PATCH** version.

  ![Custom badge](https://img.shields.io/endpoint?color=%23417B5D&url=https%3A%2F%2Frickslab.com%2Fbadges%2Fdeb_ups_version.json)
  ![Custom badge](https://img.shields.io/endpoint?color=%23417B5D&url=https%3A%2F%2Frickslab.com%2Fbadges%2Fdeb_ups_down.json)

## User Guide

For a detailed introduction, a community sourced
[User Guide](https://github.com/Ricks-Lab/ups-utils/blob/master/docs/USER_GUIDE.md)
is available. All tools are demonstrated and use cases are presented.  Additions
to the guide are welcome.  Please submit a pull request with your suggested additions!

## Commands

### ups-ls

This utility displays most relevant parameters for installed and compatible
UPSs listed in the *ups-config.json* file.  By default, all available parameters
are displayed. The *--input* and *--output* options can be used to get relevant
UPS input and output parameters.  With the *--list_commands* option, the
utility will list all available SNMP commands for the configured UPS.  With
the *--list_params* option, the daemon configuration parameters will be listed.
The *--list_decoders* option will display list of all MiB decoders available
for the UPS defined as daemon target. The *--verbose* will cause informational
messages to be displayed and *--no_markup* option will result in plain text
output instead of color coded text.  The logger is enabled with the *--debug*
option.

### ups-daemon

With no options specified, the utility will give the current status of the
UPS configured with *daemon = true* in the ups-config.json file. With the
*--daemon* option, *ups-daemon* will continuously check the status of the
UPS.  When it detects that the UPS is sourcing powering from the battery,
it will check the amount of time it has been running on battery and run
the specified suspend script when the specified threshold is exceeded.  It
will execute the specified resume script when it detects power has resumed.
When the utility detects a Battery Low event from the UPS or that time
remaining for battery or the battery charge is below specified thresholds,
then the shutdown script will be executed. If *ups-daemon* detects a return
to line power has occurred before the shutdown has completed, it will
execute the cancel shutdown script.  With the *--verbose* option set,
event update messages will be output, otherwise, only events are output.
The *--no_markup* option will cause the output to be in plain text, with
no color markup codes. The *--logfile filename* option is used to specify
a logfile, but is not implemented at this time.  The threshold and script
definitions must be made in the *ups-utils.ini* file using
*ups-utils.ini.template* as a template.  The logger is enabled with the
*--debug* option.  The *--ltz* option will result in the use of the local
time zone in the monitor window and logs.  This will be the local time of
where the app is running, not the location of the UPS.  The default is UTC.

### ups-mon

A utility to give the current state of all compatible UPSs. The default
behavior is to continuously update a text based table in the current window
until Ctrl-C is pressed.  With the *--gui* option, a table of relevant
parameters will be updated in a Gtk window.  You can specify the delay
between updates with the *--sleep N* option where N is an integer > 10 that
specifies the number of seconds to sleep between updates.  The threshold for
color coding definitions read from the *ups-utils.ini* file.  This can be
created from a template *ups-utils.ini.template*, that is part of the
installation package. *ups-utils.ini.template* as a template. The *--log*
option is used to write all monitor data to a psv log file.  When writing
to a log file, the utility will indicate this in red at the top of the
window with a message that includes the log file name.  The *--status*
option will output a table of the current status.  By default, unresponsive
UPSs will not be displayed, but the *--show_unresponsive* can be used to
force their display.  The logger is enabled with the *--debug* option.  The
*--ltz* option will result in the use of the local time zone in the
monitor window and logs.  This will be the local time of where the app is
running, not the location of the UPS.  The default is UTC.

## New in Current Release  -  v1.2.11

* Fix GObject.timeout_add deprecation.
* Update repository installation guide and add requirements file.
* Many minor changes.

## Known Issues

The utility currently supports:

* APC UPS with AP9630 and AP9641 NMC
* EATON UPS with PowerWalker NMC.  I had an issue with voltage interpretation, and
found that PowerWalker does not support the use of their NMC with Eaton UPS.  But it 
mostly works anyway.  I no longer have any Eaton UPSs for testing.

It monitors the specified UPSs using snmp v2c.  I have not implemented the
ability to listen to snmp traps yet, as I still have some research to do.
If you have different UPS and would like to extend the dictionary in this
[code](https://github.com/Ricks-Lab/ups-utils/blob/master/UPSmodules/UPSmodule.py)
to support it, feel free to make a pull request.

## Reference Material

* [apc-ups-snmp](https://github.com/phillipsnick/apc-ups-snmp)
* [Partial List of OIDs for APC UPS](https://www.opsview.com/resources/monitoring/blog/monitoring-apc-ups-useful-oids)
* [Another Partial List of OIDs for APC UPS](https://www.itninja.com/blog/view/snmp-oids-for-apc-smart-ups-3000-rm-xl)
* [Another Partial List of OIDs for APC UPS](https://wiki.netxms.org/wiki/UPS_Monitoring_(APC)_via_SNMP)
* [APC Reference](https://www.apc.com/salestools/LFLG-AFACYW/LFLG-AFACYW_R1_EN.pdf)
* [snmp utilities](http://www.net-snmp.org/docs/man/)
* [MIB Browser](http://www.ireasoning.com/)
* [Eaton PowerWalker NMC](https://powerwalker.com/?page=nmc&lang=en)

## History

### New in Previous Release  -  v1.2.10

* Optimize `ups-ls --about` output.
* Improved messaging to aid new users in configuring new setup.
* Detect specification of multiple daemon UPS.  Must only be one target daemon UPS.

### New in Previous Release  -  v1.2.9

* Fixed error handling for config file reading.
* Exit ups-daemon if no daemon ups is defined.
* Added details on adding *upsutils* group and other configuration details.

### New in Previous Release  -  v1.2.8

* Improved *ups-mon --gui* eventual stack overflow. Still hangs after long
  runs.  I need some help on this one.
* Add time of last read to *ups-mon* header.
* Implemented option to display/log in local time. Local time is the time
  where the application is running; not the location of the UPS.

### New in Previous Release  -  v1.2.7

* Updates to the User Guide.
* Cleaned up implementation of GuiComp object.
* Fixed an error in the calculation of time on battery and battery remaining
  for APC. Now just store time in minutes in data structure and drop the string version.
* Include time on battery in color coding logic.
* More code optimizations.
* Improved LOGGER.debug messages.

### New in Previous Release  -  v1.2.5

* Improved message for skipped parameters.
* Rewrite daemon configuration reader to make more robust.
* Catch errors for json and config readers and handle with feedback to user.
* User guide updates.

### New in Previous Release  -  v1.2.4

* More robust reading of config file.  Missing items will generate a warning
  message and defaults will be used.
* The PyPI installation still seems to include *ups-monitor*, so I will print
  message and inform user to use *ups-mon* instead.

### New in Previous Release  -  v1.2.3

* Fixed issue in installation instructions that indicated gpu instead of ups.
* More error checking.  Make APC NMC names backward compatible and more flexible.

### New in Previous Release  -  v1.2.2

* Fixed crash when config files are missing and improved feedback to help
  user resolve. Update documents to make more clear to user on how to setup.
* Modified the *--about* of *ups-ls* to aid user in configuring the utility.

### New in Previous Release  -  v1.2.1

* Fixed issue in referencing PyPI install resource paths.

### New in Previous Release  -  v1.2.0

* Delay sys exit on failure to allow more information to be available for user to troubleshoot.
* Check file permissions for security issues and exit if not secure.
* Determine installation type (Local Git Repository, PyPI, or Debian), and force use
  of Debian location for configuration files if it is a debian installation.
* The ups-utils.ini file is now only required for ups-daemon.  Other utilities will
  use defaults if missing.
* Added verbose option to ups-daemon to output status message for normal readings.
* Changes in documentation to describe steps necessary to secure snmp shared secret.
* Added check of configuration files readability.
* Implement code improvements from gpu-utils project.
* Move listing like functions from *ups-daemon* to *ups-ls*.
* Complete rewrite.
* USR1 signal will cause *ups-mon* and *ups-daemon* to reread daemon ini file.
* Moved logic of daemon parameter color coding to the daemon class.

### New in Previous Release  -  v1.0.0

* Initial Release - Full functionality and working debian package!
