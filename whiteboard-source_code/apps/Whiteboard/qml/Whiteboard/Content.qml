import QtQuick
import QtQuick.Controls
import QtQuick.Window
import Qt.labs.qmlmodels

import I2Quick

import Whiteboard


I2InnerPointerEventsArea {
    id: root


    //----------------------------------
    //
    // Behaviors
    //
    //----------------------------------

    onInnerReleaseEnded: {
        let whiteboardPosition = whiteboardArea.mapFromItem(root, root.scenePosition);
        Whiteboard.sendClick(whiteboardPosition);
    }

    //----------------------------------
    //
    // Content
    //
    //----------------------------------

    Rectangle {
        id: whiteboard
        objectName: "background"

        anchors {
            top: parent.top
            bottom: parent.bottom
            left: parent.left
            right: chatView.left
        }

        onColorChanged: {
            Whiteboard.backgroundColor = color;
        }

        Binding {
            target: whiteboard
            property: "color"
            value: Whiteboard.backgroundColor
        }


        Row {
            id: actions

            Button {
                text: qsTr("Clear")

                I2Cursor.cursorShape: Qt.PointingHandCursor

                onClicked: {
                    Whiteboard.clear();
                }
            }

            Button {
                text: Whiteboard.labelsVisible ? qsTr("Hide labels") : qsTr("Show labels")

                I2Cursor.cursorShape: Qt.PointingHandCursor

                enabled: Whiteboard.elements.count > 0

                onClicked: {
                    if (Whiteboard.labelsVisible)
                        Whiteboard.hideLabels();
                    else
                        Whiteboard.showLabels();
                }
            }

            Button {
                text: Whiteboard.canInteractWithElements ? qsTr("Lock elements") : qsTr("Unlock elements")

                I2Cursor.cursorShape: Qt.PointingHandCursor

                enabled: Whiteboard.elements.count > 0

                onClicked: {
                    if (Whiteboard.canInteractWithElements)
                        Whiteboard.lockElements();
                    else
                        Whiteboard.unlockElements();
                }
            }
        }


        Text {
            id: title
            objectName: "title"

            anchors {
                left: parent.left
                right: parent.right
                top: actions.bottom
            }

            horizontalAlignment: Text.AlignHCenter

            elide: Text.ElideRight

            color: WhiteboardTheme.titleColor

            font {
                family: "Asap"
                pixelSize: 48
                bold: true
            }

            onTextChanged: {
                Whiteboard.title = title.text;
            }

            Binding {
                target: title
                property: "text"
                value: Whiteboard.title
            }
        }


        Item {
            id: whiteboardArea

            anchors {
                left: parent.left
                right: parent.right
                top: title.bottom
                topMargin: 10
                bottom: parent.bottom
            }

            Binding {
                target: Whiteboard
                property: "whiteboardWidth"
                value: whiteboardArea.width
            }

            Binding {
                target: Whiteboard
                property: "whiteboardHeight"
                value: whiteboardArea.height
            }

            Item {
                id: elementsContainer

                anchors.fill: parent

                enabled: Whiteboard.canInteractWithElements

                Repeater {
                    model: Whiteboard.elements

                    delegate: DelegateChooser {
                        role: "type"

                        DelegateChoice {
                            roleValue: GraphicElementType.Text

                            delegate: Text {
                                id: textItem
                                objectName: element ? "item" + element.uid : ""

                                property TextElement element: model.qtObject

                                text: (element?.text ?? "")
                                color: (element?.color ?? "black")
                                opacity: (element?.opacity ?? 1.0)

                                font {
                                    family: "Asap"
                                    pixelSize: 36
                                }

                                onXChanged: {
                                    if (element)
                                        element.x = x;
                                }

                                onYChanged: {
                                    if (element)
                                        element.y = y;
                                }

                                Binding {
                                    target: textItem
                                    property: "x"
                                    value: (textItem.element ? textItem.element.x : 0)
                                }

                                Binding {
                                    target: textItem
                                    property: "y"
                                    value: (textItem.element ? textItem.element.y : 0)
                                }

                                DragHandler {
                                    onActiveChanged: {
                                        if (active)
                                            I2QmlUtils.setAsLastChild(textItem);
                                    }
                                }

                                ElementInfo {
                                    anchors {
                                        bottom: parent.top
                                        bottomMargin: 3
                                        horizontalCenter: parent.horizontalCenter
                                    }

                                    visible: Whiteboard.labelsVisible

                                    text: parent.objectName

                                    onClicked: {
                                        Whiteboard.removeElement(parent.element);
                                    }
                                }
                            }
                        }


                        DelegateChoice {
                            roleValue: GraphicElementType.Rectangle

                            delegate: I2SvgRectangle {
                                id: rectangleItem
                                objectName: element ? "item" + element.uid : ""

                                property ShapeElement element: model.qtObject

                                width: (element?.width ?? 0)
                                height: (element?.height ?? 0)

                                fill: (element?.fill ?? "white")

                                stroke: (element?.stroke ?? "black")
                                strokeWidth: (element?.strokeWidth ?? 0)

                                opacity: (element?.opacity ?? 1.0)

                                antialiasing: false

                                onXChanged: {
                                    if (element)
                                        element.x = x;
                                }

                                onYChanged: {
                                    if (element)
                                        element.y = y;
                                }

                                Binding {
                                    target: rectangleItem
                                    property: "x"
                                    value: (rectangleItem.element ? rectangleItem.element.x : 0)
                                }

                                Binding {
                                    target: rectangleItem
                                    property: "y"
                                    value: (rectangleItem.element ? rectangleItem.element.y : 0)
                                }

                                DragHandler {
                                    onActiveChanged: {
                                        if (active)
                                            I2QmlUtils.setAsLastChild(rectangleItem);
                                    }
                                }

                                ElementInfo {
                                    anchors {
                                        bottom: parent.top
                                        bottomMargin: 3 + Math.round(parent.strokeWidth/2)
                                        horizontalCenter: parent.horizontalCenter
                                    }

                                    visible: Whiteboard.labelsVisible

                                    text: parent.objectName

                                    onClicked: {
                                        Whiteboard.removeElement(parent.element);
                                    }
                                }
                            }
                        }


                        DelegateChoice {
                            roleValue: GraphicElementType.Ellipse

                            delegate: I2SvgEllipse {
                                id: ellipseItem
                                objectName: element ? "item" + element.uid : ""

                                property ShapeElement element: model.qtObject

                                useSvgGeometry: false
                                width: (element?.width ?? 0)
                                height: (element?.height ?? 0)

                                fill: (element?.fill ?? "white")

                                stroke: (element?.stroke ?? "black")
                                strokeWidth: (element?.strokeWidth ?? 0)

                                opacity: (element?.opacity ?? 1.0)

                                antialiasing: false

                                onXChanged: {
                                    if (element)
                                        element.x = x;
                                }

                                onYChanged: {
                                    if (element)
                                        element.y = y;
                                }

                                Binding {
                                    target: ellipseItem
                                    property: "x"
                                    value: (ellipseItem.element ? ellipseItem.element.x : 0)
                                }

                                Binding {
                                    target: ellipseItem
                                    property: "y"
                                    value: (ellipseItem.element ? ellipseItem.element.y : 0)
                                }

                                DragHandler {
                                    onActiveChanged: {
                                        if (active)
                                            I2QmlUtils.setAsLastChild(ellipseItem);
                                    }
                                }

                                ElementInfo {
                                    anchors {
                                        bottom: parent.top
                                        bottomMargin: 3 + Math.round(parent.strokeWidth/2)
                                        horizontalCenter: parent.horizontalCenter
                                    }

                                    visible: Whiteboard.labelsVisible

                                    text: parent.objectName

                                    onClicked: {
                                        Whiteboard.removeElement(parent.element);
                                    }
                                }
                            }
                        }


                        DelegateChoice {
                            roleValue: GraphicElementType.Image

                            delegate: AnimatedImage {
                                id: imageItem
                                objectName: element ? "item" + element.uid : ""

                                property ImageElement element: model.qtObject

                                width: (element && element.explicitWidth) ? element.width : implicitWidth
                                height: (element && element.explicitHeight) ? element.height : implicitHeight

                                source: (element?.source ?? "")

                                opacity: (element?.opacity ?? 1.0)

                                onXChanged: {
                                    if (element)
                                        element.x = x;
                                }

                                onYChanged: {
                                    if (element)
                                        element.y = y;
                                }

                                Binding {
                                    target: imageItem
                                    property: "x"
                                    value: (imageItem.element ? imageItem.element.x : 0)
                                }

                                Binding {
                                    target: imageItem
                                    property: "y"
                                    value: (imageItem.element ? imageItem.element.y : 0)
                                }

                                DragHandler {
                                    onActiveChanged: {
                                        if (active)
                                            I2QmlUtils.setAsLastChild(imageItem);
                                    }
                                }

                                ElementInfo {
                                    anchors {
                                        bottom: parent.top
                                        bottomMargin: 3
                                        horizontalCenter: parent.horizontalCenter
                                    }

                                    visible: Whiteboard.labelsVisible

                                    text: parent.objectName

                                    onClicked: {
                                        Whiteboard.removeElement(parent.element);
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    } 

    ChatView {
        id: chatView

        anchors {
            top: configureNetwork.bottom
            bottom: parent.bottom
            right: parent.right
        }
    }

    ConfigureNetwork {
        id: configureNetwork
        anchors {
            top: parent.top
            right: parent.right
        }
        width: chatView.width
    }
}
