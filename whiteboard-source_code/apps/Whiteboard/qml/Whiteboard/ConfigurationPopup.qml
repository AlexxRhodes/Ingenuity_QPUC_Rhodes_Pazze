import QtQuick
import QtQuick.Controls.Fusion

import I2Quick

import Whiteboard

Rectangle {
    id: root
    implicitWidth: 250
    implicitHeight: popupContent.y + popupContent.implicitHeight

    QtObject {
        id: rootPrivate

        property bool isConnected: NetworkConfiguration.isConnected
    }

    MouseArea {
        anchors.fill: parent
        onClicked: {
            root.forceActiveFocus();
        }
    }

    Column {
        id: popupContent
        anchors {
            top:parent.top
            topMargin: 10
            left: parent.left
            leftMargin: 10
            right: parent.right
            rightMargin: 10
        }

        spacing: 10

        Item {
            id: comboBoxitem

            anchors {
                left: parent.left
                right: parent.right
            }

            height: childrenRect.height

            Text {
                id: textComboBox
                text: qsTr("Network device")
            }

            ComboBox {
                anchors {
                    top: textComboBox.bottom
                    left: parent.left
                    right: parent.right
                }

                model: NetworkConfiguration.availableNetworkDevicesPrettyPrinted
                currentIndex: NetworkConfiguration.availableNetworkDevices.indexOf(NetworkConfiguration.currentNetworkDevice)

                onActivated: {
                    if (currentValue !== "")
                    {
                        if (rootPrivate.isConnected)
                            NetworkConfiguration.disconnectFromIngescape();

                        NetworkConfiguration.currentNetworkDevice = NetworkConfiguration.availableNetworkDevices[currentIndex];
                        focus = false;
                    }
                }
            }
        }

        Item {
            anchors {
                left: parent.left
                right: parent.right
            }
            height: childrenRect.height + 5 //offset

            Text {
                id: textTextfield
                text: qsTr("Port")
            }

            TextField {
                id: currentPort
                anchors {
                    top: textTextfield.bottom
                    left: parent.left
                    right: parent.right
                }

                text: NetworkConfiguration.currentPort

                validator: IntValidator {
                    bottom: 1
                    top: 65535
                }

                onActiveFocusChanged: {
                    if (!activeFocus && text.length !== 0 && acceptableInput)
                    {
                        if (rootPrivate.isConnected)
                            NetworkConfiguration.disconnectFromIngescape();

                        NetworkConfiguration.currentPort = Number(text);
                    }
                }

                onAccepted: {
                    focus = false;
                }

                Binding {
                    target: currentPort
                    property: "text"
                    value: NetworkConfiguration.currentPort
                    when: !currentPort.activeFocus
                }
            }
        }
    }
}
