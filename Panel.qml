import QtQuick
import Quickshell
import qs.Commons
import qs.Ui

// Help text only: never auto-run CLI or privileged commands.
Panel {
    id: root
    moduleName: "community.omarchy-ssh-guard"
    manageIpc: false
    property var anchorItem: null
    property var hostWidget: null

    function open() { root.controller.show() }
    function close() { root.controller.hide() }
    function switchPanel(direction) {
        if (root.bar && typeof root.bar.switchPanelFrom === "function")
            return root.bar.switchPanelFrom(root.hostWidget || root, direction)
        return false
    }

    KeyboardPanel {
        id: popup
        anchorItem: root.anchorItem
        owner: root.hostWidget || root
        bar: root.bar
        open: root.opened
        focusTarget: catcher
        contentWidth: popup.fittedContentWidth(Style.space(300))
        contentHeight: popup.fittedContentHeight(content.implicitHeight)
        PanelKeyCatcher {
            id: catcher
            anchors.fill: parent
            onCloseRequested: root.close()
            onTabRequested: function(direction) { root.switchPanel(direction) }
            Column {
                id: content
                width: parent.width
                spacing: Style.space(10)
                Text {
                    width: parent.width
                    text: "Security status: NOT VERIFIED"
                    color: root.barForeground
                    font.pixelSize: Style.font.subtitle
                    font.bold: true
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: "Terminal: omarchy-guard audit"
                    color: root.barForeground
                    font.pixelSize: Style.font.body
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: "Read README.md for the SSH checklist, independent reachability tests and rollback requirements."
                    color: root.barForeground
                    font.pixelSize: Style.font.body
                    wrapMode: Text.WordWrap
                }
                Text {
                    width: parent.width
                    text: "No firewall edits, key reads or privilege requests. Unknown is not secure."
                    color: root.barForeground
                    font.pixelSize: Style.font.body
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
