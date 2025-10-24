#!/bin/bash

AppExist=`ps -C "ESI100"|grep ESI100` ; if test ${#AppExist} -gt 20; then echo "EXIST"&&exit 0; else echo "Not exist"; fi

function MsgBox() {
        if [ $# -lt 1 ] ; then
                content="Dialog content here!"
        else
                content=${1}
        fi
        cmd="zenity --error --title \"Error Dialog\" --text \"${content}\" 11 100 --width=400 --height=200"
        #echo ${cmd}
        eval ${cmd}
}

function TestPCIeConnection() {
	MSG=`lspci -d 10ee: -nx|grep -E "ee 10 38 80|ee 10 38 90"|awk '{print $6}'`
	if [ -z "${MSG}" ] ; then
		MsgBox "USE Board not Found in PCIe. Please reboot!!!"
		exit -1;
	fi
	let "value=$((${MSG:1}))&6"
	echo ${value}
	if [ ${value} -ne 6 ] ; then
		MsgBox "USE Board PCIe Status Error! should be BIT3 is 1? (now is:${MSG}) Please reboot!!!"
		exit -1;
	else
		echo "PCIe ok..."
	fi
}

function TestRunningMode(){
	IsSimulation=`cat ~/ESI/config/systemconfig.ini |grep SimulateMode|awk -F '=' '{print $2}'`
	if test ${IsSimulation} = "true" ; then
		echo "Simulation=true" ;
	else 
		echo "Simulation=false"; 
		TestPCIeConnection;
	fi
}

function startInputEventsCapturer() {
    echo "start input-events."
    (cd ${dir} && ./start_inputEventsCapturer.sh prod)
    echo -e "start input-events...${GREEN}OK${NOCOLOR}"
}

function disableSystemShortcuts() {
    gsettings set org.gnome.desktop.wm.keybindings toggle-maximized []
    gsettings set org.gnome.desktop.wm.keybindings panel-run-dialog []
    gsettings set org.gnome.desktop.wm.keybindings close []
    gsettings set org.gnome.desktop.wm.keybindings begin-move []
    gsettings set org.gnome.desktop.wm.keybindings begin-resize []
    gsettings set org.gnome.desktop.wm.keybindings unmaximize []
    gsettings set org.gnome.desktop.wm.keybindings cycle-group []
    gsettings set org.gnome.desktop.wm.keybindings cycle-group-backward []
    gsettings set org.gnome.desktop.wm.keybindings panel-main-menu []
    gsettings set org.gnome.desktop.wm.keybindings panel-run-dialog []
    gsettings set org.gnome.desktop.wm.keybindings toggle-maximized []
    gsettings set org.gnome.shell.keybindings open-application-menu []
    #gsettings set org.gnome.shell.keybindings toggle-overview []
}

function disableKeyRepeat() {
    xset -r r off
}

function disableVirtualKeyboard() {
    $dir/../scripts/disable_embedded_keyboard.sh
    #gsettings set org.gnome.desktop.a11y.applications screen-keyboard-enabled false
}

GREEN='\033[5;47;32m'
SPLASH='\033[0;5m'
NOCOLOR='\033[0m'
 
dir=`dirname $0`
export LD_LIBRARY_PATH=$dir/../lib:$dir/../lib/vtk
export QT_PLUGIN_PATH=$dir/../lib
export QML2_IMPORT_PATH=$dir/qml
export ESI_PATH=/opt/esi100/bin

if [ -f /usr/share/backgrounds/esi/background.jpg ]; then
    gsettings set org.gnome.desktop.background picture-uri "file:/usr/share/backgrounds/esi/background.jpg"
else
    gsettings set org.gnome.desktop.background picture-uri "file:/opt/esi100/resources/images/background.jpg"
fi
gsettings set org.gnome.desktop.session idle-delay 86000
gsettings set org.gnome.desktop.screensaver lock-enabled false
gsettings set org.gnome.mutter overlay-key 'Super_R'
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type 'nothing'
gsettings set org.gnome.settings-daemon.plugins.power power-button-action 'nothing'
gsettings set org.gnome.system.location enabled true
gsettings set org.gnome.system.location allowed-apps "['gnome-control-center']"

TestRunningMode

disableSystemShortcuts
disableKeyRepeat
disableVirtualKeyboard
startInputEventsCapturer

echo "starting ESI100..."
$dir/ESI100 $* &

sleep 5
if [ -d /home/esi/esi_ai ]; then
    ( cd /home/esi/esi_ai
      ./app/runqt.sh
    )
fi
