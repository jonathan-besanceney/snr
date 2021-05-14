# Save and Restore - SnR

![Image of Supernova Remanent - SNR](https://***REMOVED***/gitlab/kubernetes/snr/raw/develop/images/300px-Keplers_supernova.jpg)

Small tool to make applications (databases and files) save and restore easy. 

It comes with a CLI providing these functionalities. You can run `snr -h` to get extra informations.
- **daemon** : launch snr as a service, relying on its internal scheduler to trigger configured application saves process. You may want to integrate it with your init system - see following **create-systemd-service** section
- **save** : list applications ready to save - some may be restore only, convenient for testing - , or save a particular app. Save process is the following :
  - launch databases and files save commands in parallel - remember that point when updating configuration, specially compression section. Don't run all saves at the same time ! 
  - if configured, run save retention to keep only wanted save files. More details in save.sample.yaml
- **restore** : list applications ready to restore, or restore specified application. Here also, all commands are run in parallel.
- **genconf** : Write sample configuration file in /etc/snr/save.yaml and exit
- **create-systemd-service** : Create systemd service in /etc/systemd/system/snr.service and exit

## Requirements

- python >= 3.6
- tar
- xz
- lzop (useful if you have large amount of files)
- mysql client
- postgresql client

## Installation

```
git clone git@github.com:jonathan-besanceney/snr.git
cd snr
python setup.py install
```
