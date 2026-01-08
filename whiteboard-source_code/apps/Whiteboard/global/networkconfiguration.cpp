/*
 *  Whiteboard
 *
 *  Copyright © 2024 Ingenuity i/o. All rights reserved.
 *
 *  See license terms for the rights and conditions
 *  defined by copyright holders.
 *
 *  Contributors:
 *    Brandon Gutierrez <gutierrez@ingenuity.io>
 *
 */

#include "networkconfiguration.h"


#ifdef Q_OS_MACOS
#include <CoreFoundation/CoreFoundation.h>
#include <SystemConfiguration/SystemConfiguration.h>
#endif

static const QString NETWORK_CONFIGURATION_DEFAULT_IP {"127.0.0.1"};


void monitorCallback(igs_monitor_event_t event, const char *device, const char *ipAddress, void *myData)
{
    IGS_UNUSED(ipAddress);

    auto networkConfig = static_cast<NetworkConfiguration*>(myData);
    Q_ASSERT(networkConfig);

    auto deviceStr = QString::fromLocal8Bit(device);
    switch (event)
    {
    case IGS_NETWORK_OK:
        qInfo() << "Network device" << deviceStr << "is available again";
        break;

    case IGS_NETWORK_DEVICE_NOT_AVAILABLE:
        qInfo() << "Network device" << deviceStr << "became unavailable";
        Q_EMIT networkConfig->deviceNoMoreAvailable(deviceStr);
        break;

    case IGS_NETWORK_ADDRESS_CHANGED:
        qInfo() << "Network device" << deviceStr << "IP address changed";
        Q_EMIT networkConfig->deviceNoMoreAvailable(deviceStr);
        break;

    case IGS_NETWORK_OK_AFTER_MANUAL_RESTART:
        qInfo() << "Network device" << deviceStr << "is available again (after manual restart)";
        break;

    default:
        break;
    }
}


NetworkConfiguration::NetworkConfiguration(QObject* parent)
    : QObject{parent}
    , _currentIpAddress(NETWORK_CONFIGURATION_DEFAULT_IP)
    , _currentPort(5670)
{
    QQmlEngine::setObjectOwnership(this, QQmlEngine::CppOwnership);

    // Network settings
    setcurrentNetworkDevice("");
    setcurrentPort(5670);

    char **devices = nullptr;
    char **addresses = nullptr;
    int nbD = 0;
    int nbA = 0;
    devices = igs_net_devices_list(&nbD);
    addresses = igs_net_addresses_list(&nbA);
    Q_ASSERT(nbD == nbA);

    bool deviceIsViable = false;
    if (!_currentNetworkDevice.isEmpty())
    {
        for (int i(0) ; (i < nbD) && !deviceIsViable ; ++i)
            deviceIsViable = (_currentNetworkDevice == QString::fromLocal8Bit(devices[i]));
    }

    if (deviceIsViable)
        qInfo() << "using last used network device (" << _currentNetworkDevice << ")";
    else
    {
        if (nbD == 1)
        {
            //exactly one compliant network device available: we use it
            setcurrentNetworkDevice(QString::fromLocal8Bit(devices[0]));
            qInfo() << "using" << _currentNetworkDevice << "as default network device (this is the only one available)";
        }
        else if ((nbD == 2)
                 && ((strcmp(addresses[0], "127.0.0.1") == 0)
                     || (strcmp(addresses[1], "127.0.0.1") == 0)))
        {
            //two devices, one of which is the loopback
            //pick the device that is NOT the loopback
            const char* selectedDevice = (strcmp(addresses[0], "127.0.0.1") == 0) ? devices[1] : devices[0];
            setcurrentNetworkDevice(QString::fromLocal8Bit(selectedDevice));
            qInfo() << "using" << _currentNetworkDevice << "as default network device (this is the only one available that is not the loopback)";
        }
        else
        {
            setcurrentNetworkDevice("");
            if (nbD == 0)
                qWarning() << "No network device found.";
            else
                qWarning() << "Several network devices available. None will be selected by default.";
        }
    }

    igs_free_net_devices_list(devices, nbD);
    igs_free_net_addresses_list(addresses, nbD);

    igs_monitor_set_start_stop(false);
    igs_observe_monitor(monitorCallback, this);

    connect(this, &NetworkConfiguration::deviceNoMoreAvailable, this, &NetworkConfiguration::_onDeviceNoMoreAvailable);
    connect(this, &NetworkConfiguration::availableNetworkDevicesChanged, this, &NetworkConfiguration::_updatePrettyPrintedList);

    updateAvailableNetworkDevices();
}


NetworkConfiguration& NetworkConfiguration::instance()
{
    static NetworkConfiguration _instance;
    return _instance;
}


QObject* NetworkConfiguration::qmlSingleton(QQmlEngine* engine, QJSEngine* scriptEngine)
{
    Q_UNUSED(engine)
    Q_UNUSED(scriptEngine)

    return &NetworkConfiguration::instance();
}


void NetworkConfiguration::setavailableNetworkDevices(I2BestTypeDef<QStringList> value)
{
    if (_availableNetworkDevices != value)
    {
        _availableNetworkDevices = value;
        updateNetworkDevicesFriendlyNamesCache();
        Q_EMIT availableNetworkDevicesChanged();
    }
}


void NetworkConfiguration::updateAvailableNetworkDevices()
{
    QStringList devices;
    char** deviceList = nullptr;
    int deviceCount = 0;
    deviceList = igs_net_devices_list(&deviceCount);

    for (int i(0) ; i < deviceCount ; ++i)
        devices.append(QString::fromLocal8Bit(deviceList[i]));

    igs_free_net_devices_list(deviceList, deviceCount);
    devices.sort(Qt::CaseInsensitive);

    setavailableNetworkDevices(devices);
}


bool NetworkConfiguration::networkDeviceIsAvailable(const QString& deviceName)
{
    return _availableNetworkDevices.contains(deviceName);
}


QString NetworkConfiguration::getNetworkDeviceFriendlyName(const QString& deviceName, bool updateCacheIfNeeded)
{
#ifdef Q_OS_MACOS
    auto result = _networkDevicesSystemNameToFriendlyName.value(deviceName);
    if (result.isEmpty() && updateCacheIfNeeded)
    {
        updateNetworkDevicesFriendlyNamesCache();
        result = getNetworkDeviceFriendlyName(deviceName, false);
    }
    return result;
#elif defined(Q_OS_WIN)
    // Windows: deviceName is already a friendly name (see ziflist.c)
    Q_UNUSED(updateCacheIfNeeded)
    return deviceName;
#else
    Q_UNUSED(deviceName)
    Q_UNUSED(updateCacheIfNeeded)
    return {};
#endif
}


void NetworkConfiguration::updateNetworkDevicesFriendlyNamesCache()
{
#ifdef Q_OS_MACOS
    _networkDevicesSystemNameToFriendlyName.clear();

    CFArrayRef networkInterfaces = SCNetworkInterfaceCopyAll();
    if (networkInterfaces)
    {
        CFIndex count = CFArrayGetCount(networkInterfaces);
        for (CFIndex index = 0; index < count; index++)
        {
            SCNetworkInterfaceRef networkInterface = (SCNetworkInterfaceRef) CFArrayGetValueAtIndex(networkInterfaces, index);
            CFStringRef bsdName = SCNetworkInterfaceGetBSDName(networkInterface);
            if (bsdName)
            {
                CFStringRef prettyName = SCNetworkInterfaceGetLocalizedDisplayName(networkInterface);
                if (prettyName)
                    _networkDevicesSystemNameToFriendlyName.insert(QString::fromCFString(bsdName), QString::fromCFString(prettyName));
            }
        }

        CFRelease(networkInterfaces);
    }
#endif
}


igs_result_t NetworkConfiguration::connectToIngescape()
{
    Q_ASSERT(!_currentNetworkDevice.isEmpty());
    Q_ASSERT(_currentPort > 0);

    if (igs_is_started())
        return IGS_SUCCESS;

    igs_result_t result = IGS_SUCCESS;

    if (result == IGS_SUCCESS)
        result = igs_start_with_device(_currentNetworkDevice.toLocal8Bit().toStdString().c_str(), _currentPort);

    if (result == IGS_SUCCESS)
    {
        _stopMonitoring();
        _startMonitoring(_currentNetworkDevice, static_cast<int>(_currentPort));

        setisConnected(true);
    }
    else
        Q_EMIT igsConnectionFailed();

    return result;
}


void NetworkConfiguration::disconnectFromIngescape(bool forceStop)
{
    _stopMonitoring();
    if (forceStop || igs_is_started())
    {
        disconnectFromIngescapeWithoutStop();
        igs_stop();
    }
}


void NetworkConfiguration::disconnectFromIngescapeWithoutStop()
{
    if (igs_is_started())
    {
        igs_disable_security();
        setisConnected(false);
    }
}


void NetworkConfiguration::_startMonitoring(const QString& device, const int port) const
{
    if (!igs_monitor_is_running())
        igs_monitor_start_with_network(MONITORING_TIMEOUT_MS, device.toLocal8Bit().toStdString().c_str(), port);
}


void NetworkConfiguration::_stopMonitoring() const
{
    if (igs_monitor_is_running())
        igs_monitor_stop();
}


void NetworkConfiguration::_onDeviceNoMoreAvailable(const QString& device)
{
    if (device == _currentNetworkDevice)
    {
        disconnectFromIngescape();
        setcurrentNetworkDevice("");
        Q_EMIT openNetworkConfiguration();
    }
}

void NetworkConfiguration::_updatePrettyPrintedList()
{
    _availableNetworkDevicesPrettyPrinted.clear();
    for (auto device : _availableNetworkDevices.toList())
        _availableNetworkDevicesPrettyPrinted.append(QString("%1 (%2)").arg(device, getNetworkDeviceFriendlyName(device)));
}


void NetworkConfiguration::setcurrentNetworkDevice(I2BestTypeDef<QString> value)
{
    if (_currentNetworkDevice != value)
    {
        _currentNetworkDevice = value;

        char** addressesList = nullptr;
        int addressesCount = 0;
        addressesList = igs_net_addresses_list(&addressesCount);

        char** devicesList = nullptr;
        int devicesCount = 0;
        devicesList = igs_net_devices_list(&devicesCount);
        if (devicesCount == addressesCount)
        {
            auto currentNetworkDeviceAsStdString = _currentNetworkDevice.toLocal8Bit().toStdString();
            for (int i(0) ; i < devicesCount ; ++i)
            {
                if (strcmp(devicesList[i], currentNetworkDeviceAsStdString.c_str()) == 0)
                {
                    setcurrentIpAddress(QString(addressesList[i]));
                    break;
                }
            }
        }
        else
        {
            qWarning() << "igs_net_addresses_list and igs_net_devices_list have not return the same number of items. IP address can not be set";
            setcurrentIpAddress(NETWORK_CONFIGURATION_DEFAULT_IP);
        }
        igs_free_net_devices_list(devicesList, devicesCount);
        igs_free_net_addresses_list(addressesList, addressesCount);

        Q_EMIT currentNetworkDeviceChanged(_currentNetworkDevice);
    }
}


void NetworkConfiguration::setcurrentIpAddress(I2BestTypeDef<QString> value)
{
    if (_currentIpAddress != value)
    {
        _currentIpAddress = value;
        Q_EMIT currentIpAddressChanged(_currentIpAddress);
    }
}


void NetworkConfiguration::setcurrentPort(I2BestTypeDef<uint> value)
{
    if (_currentPort != value)
    {
        _currentPort = value;
        Q_EMIT currentPortChanged(_currentPort);
    }
}
