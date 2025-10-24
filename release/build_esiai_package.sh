#!/bin/bash

DSTDIR="/home/esi/esi_ai_target"
DT=`date "+%Y%m%d"`
PKGNAME=esiai
BUILD_NUMBER_1=`echo ${BUILD_NUMBER} | awk '{printf("%05d\n",$0)}'`
VERSION=1.00.00.${DT}
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/home/jenkins/Qt/5.15.2/gcc_64/lib
export PATH=$PATH:/home/jenkins/Qt/5.15.2/gcc_64/bin

build_package() {
    PKGDIR="/home/esi/${PKGNAME}_${VERSION}_amd64"
    rm -rf /home/esi/esiai_1.00.*
    mkdir -p $PKGDIR/opt/esiai
    cp -r ${PKGNAME}_1.x_amd64/* $PKGDIR
    cp -r $DSTDIR/* $PKGDIR/opt/esiai
    (cd $PKGDIR/opt/esiai; rm -rf enhancement pics release system scripts)
    cp -r /opt/esiai/env01 $PKGDIR/opt/esiai
    #cp -r /opt/esiai/sherpa-onnx-streaming-paraformer-bilingual-zh-en $PKGDIR/opt/esiai
    cp -r /opt/esiai/sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20 $PKGDIR/opt/esiai
    rm $PKGDIR/opt/esiai/env01/bin/python3
    cp -r /usr/bin/python3.9 $PKGDIR/opt/esiai/env01/bin/python3


    sed -i "s/^Version:.*/Version: ${VERSION}/" ${PKGDIR}/DEBIAN/control
 
    (
        cd ${PKGDIR}/..
        dpkg-deb --build ${PKGNAME}_${VERSION}_amd64
        echo "Build esiai deb package finished."

        ssh esi@192.168.1.207 "cd /var/www/html/esi_packages_release/repos/1.x/esi; rm -f esiai_*.deb"
        scp esiai_*.deb esi@192.168.1.207:/var/www/html/esi_packages_release/repos/1.x/esi
        #ssh esi@192.168.1.207 "cd /var/www/html/esi_packages_release/; ./update_esi_repository.sh"
    )
}

build_package
