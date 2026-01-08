import QtQuick
import QtQuick.Controls.Basic

import I2Quick

import Whiteboard

Item {
    id: root


    //----------------------------------
    //
    // Properties
    //
    //----------------------------------
    implicitWidth: 400
    implicitHeight: 40


    QtObject {
        id: rootPrivate

        property bool isConfigurationPanelOpened: false
        property bool configurationPanelAnimationEnabled: false

        property bool isConnected: NetworkConfiguration.isConnected

        property bool isPortValid: 0 < NetworkConfiguration.currentPort && NetworkConfiguration.currentPort < 65535

        onIsConnectedChanged: {
            if (isConnected)
                networkDevicesTimer.stop();
            else
                networkDevicesTimer.start();
        }
    }


    //----------------------------------
    //
    // Behavior
    //
    //----------------------------------

    Timer {
        id: networkDevicesTimer

        interval: root.isConfigurationPanelOpened ? 1000 : 5000

        repeat: true

        onTriggered: {
            NetworkConfiguration.updateAvailableNetworkDevices();
            if (NetworkConfiguration.currentNetworkDevice !== ""
                    && !NetworkConfiguration.networkDeviceIsAvailable(NetworkConfiguration.currentNetworkDevice))
            {
                NetworkConfiguration.currentNetworkDevice = ""
                rootPrivate.isConfigurationPanelOpened = true;
            }
        }
    }

    Component.onCompleted: {
        networkDevicesTimer.start();
    }

    //----------------------------------
    //
    // Content
    //
    //----------------------------------

    ConfigurationPopup {
        id: configurationPopup
        anchors{
            right: parent.right
            top: parent.bottom
            topMargin: rootPrivate.isConfigurationPanelOpened ? 0 : -implicitHeight - root.implicitHeight
        }

        visible: (y + height) > 0

        Behavior on anchors.topMargin {
            enabled: rootPrivate.configurationPanelAnimationEnabled

            NumberAnimation {}
        }
    }

    Rectangle {
        anchors.fill: parent
        color: WhiteboardTheme.networkConfigBackgroundColor
    }

    Switch {
        id: connectionSwitch
        anchors {
            verticalCenter: configurationButton.verticalCenter
            right: configurationButton.left
        }

        height: 16
        text: rootPrivate.isConnected ? "" : qsTr("Connect")
        checked: rootPrivate.isConnected

        onToggled: {
            if (rootPrivate.isConnected)
                NetworkConfiguration.disconnectFromIngescape()
            else if (rootPrivate.isPortValid && NetworkConfiguration.currentNetworkDevice != "")
                NetworkConfiguration.connectToIngescape();
        }

        contentItem: Text {
            rightPadding: connectionSwitch.indicator.width + connectionSwitch.spacing
            text: connectionSwitch.text
            font {
                family: "Asap"
                pixelSize: 13
                bold: true
            }
            color: WhiteboardTheme.networkConfigMessageTextColor
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignHCenter
        }

        indicator: Rectangle {
            implicitWidth: 40
            implicitHeight: parent.height
            x: connectionSwitch.width - width - connectionSwitch.rightPadding
            radius: 7
            color: connectionSwitch.checked ? "#F7B942" : "transparent"
            border.color: "grey"

            Rectangle {
                x: connectionSwitch.checked ? parent.width - width : 0
                y: parent.height / 2 - height / 2
                width: 20
                height: 20
                radius: 10
                color: connectionSwitch.down ? "#cccccc" : "#ffffff"
            }
        }
    }

    Button {
        id: configurationButton
        anchors {
            verticalCenter: parent.verticalCenter
            right: parent.right
            rightMargin: 10
        }
        width: contentItem.implicitWidth + 20
        height: 30

        onClicked: {
            if (!rootPrivate.isConfigurationPanelOpened)
                NetworkConfiguration.updateAvailableNetworkDevices();

            rootPrivate.configurationPanelAnimationEnabled = true;
            rootPrivate.isConfigurationPanelOpened = !rootPrivate.isConfigurationPanelOpened;
            rootPrivate.configurationPanelAnimationEnabled = false;
        }

        contentItem: Text {
            color: WhiteboardTheme.networkConfigMessageTextColor

            text: NetworkConfiguration.currentNetworkDevice + " | " + NetworkConfiguration.currentPort

            font {
                family: "Asap"
                pixelSize: 18
            }

            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }

        background: Rectangle {
            color: configurationButton.down ? WhiteboardTheme.networkConfigBtnPressed : configButtonHover.hovered ? WhiteboardTheme.networkConfigBtnHover : WhiteboardTheme.networkConfigBtnColor
            radius: 7
        }

        HoverHandler {
            id: configButtonHover
        }
    }
}
