#!/bin/bash

#first build the DB rpm
echo "Building Measurements-Metrics-Db rpm"
rm -rf setup.py setup.cfg
cp setup/setup_Db.py setup.py
cp setup/setup_Db.cfg setup.cfg

python setup.py bdist_rpm

echo "Building Measurements-Metrics-Web rpm"
rm -rf setup.py setup.cfg
cp setup/setup_Web.py setup.py
cp setup/setup_Web.cfg setup.cfg

python setup.py bdist_rpm

rm -rf setup.py setup.cfg
cat changelog.txt >> build/bdist.linux-x86_64/rpm/SPECS/osg-measurements-metrics-db.spec
cat changelog.txt >> build/bdist.linux-x86_64/rpm/SPECS/osg-measurements-metrics-web.spec
cd build/bdist.linux-x86_64/rpm/
rpmbuild --define "_topdir $PWD" -bs SPECS/osg-measurements-metrics-db.spec
rpmbuild --define "_topdir $PWD" -bs SPECS/osg-measurements-metrics-web.spec
echo done...

