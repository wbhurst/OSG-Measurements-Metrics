
import re
import sys
import time
import types
import urllib
import urllib2
import calendar
import datetime
import json
import os.path
import string
from xml.dom.minidom import parse
import ConfigParser
import cherrypy 
from pkg_resources import resource_stream
from operator import itemgetter, attrgetter

from graphtool.base.xml_config import XmlConfig
from auth import Authenticate
from gratia.web.gratia_urls import GratiaURLS

########################################################################
# supplies "year" "month" interval for web page queries - 2014Jan22 - wbh
########################################################################
def gratia_interval(year, month):
    info = {}
    info['starttime'] = datetime.datetime(year, month, 1, 0, 0, 0)
    last_day = calendar.monthrange(year, month)[1]
    info['endtime'] = datetime.datetime(year, month, last_day, 23, 59, 59)
    return info

class WLCGReporter(Authenticate):

    ########################################################################
    # Extracts data text from xml doc page - 2014Jan22 - wbh
    ########################################################################
    def getText(self, nodelist):
	    rc = ""
	    for node in nodelist:
	        if node.nodeType == node.TEXT_NODE:
	            rc = rc + node.data
	    return rc

    ########################################################################
    # CPU info extracted from xml page
    ########################################################################
    def getcpuinfodictionary(self):
        srchUrl = 'CpuInfoUrl'
        modName = 'getcpuinfodictionary'
        print "%s: srchUrl: %s" % (modName, srchUrl)
        try:
            urlcpuinfo = getattr(globals()['GratiaURLS'](), 'GetUrl')(srchUrl)
            print "%s: SUCCESS: getattr(globals()['GratiaURLS'](), 'GetUrl')(%s)" % (modName,srchUrl)
            print "%s: retUrl: %s" % (modName, urlcpuinfo)
        except:
            print "%s: FAILED: getattr(globals()['GratiaURLS'](), 'GetUrl')(urlname=%s)" % (modName,srchUrl)
            pass
	xmldoc = urllib2.urlopen(urlcpuinfo)
	dom = parse(xmldoc)
	hepspecCpuDict = {}
	normconstCpuDict = {}
	for rowDom in dom.getElementsByTagName('CPUInfo'):
	    cpuname=self.getText((rowDom.getElementsByTagName("Name")[0]).childNodes).upper().replace(' ', '')
	    hepspec=self.getText((rowDom.getElementsByTagName("HEPSPEC")[0]).childNodes)
            normconstant = self.getText((rowDom.getElementsByTagName("NormalizationConstant")[0]).childNodes) 
	    hepspecCpuDict[cpuname]=hepspec
	    normconstCpuDict[cpuname]=normconstant
        return hepspecCpuDict,normconstCpuDict

    ###########################################################################
    # key data source function - 2014Jan22 - wbh
    ###########################################################################
    def get_apel_data(self, year=datetime.datetime.now().year, month=datetime.datetime.now().month):
        srchUrl = 'ApelUrl'
        modName = 'get_apel_data'
        print "%s: srchUrl: %s" % (modName, srchUrl)
        try:
            apel_url = getattr(globals()['GratiaURLS'](), 'GetUrl')(srchUrl)
            print "%s: SUCCESS: getattr(globals()['GratiaURLS'](), 'GetUrl')(%s)" % (modName,srchUrl)
            print "%s: retUrl: %s" % (modName, apel_url)
        except:
            print "%s: FAILED: getattr(globals()['GratiaURLS'](), 'GetUrl')(urlname=%s)" % (modName,srchUrl)
            pass
        usock = urllib2.urlopen(apel_url)
        data = usock.read()
        usock.close()
        apel_data = []
        fed_rpt = []
        datafields = []
        numcells=13
        report_time = None
        for i in range(numcells):
            datafields.append(0)
        datafields[0]="ResourceGroup"
        datafields[1]="NormFactor"
        datafields[2]="LCGUserVO"
        datafields[3]="Njobs"
        datafields[4]="SumCPU"
        datafields[5]="SumWCT"
        datafields[6]="Norm_CPU"
        datafields[7]="Norm_WCT"
        datafields[8]="RecordStart"
        datafields[9]="RecordEnd"
        datafields[10]="MeasurementDate"
        datafields[11]="FederationName"
        datafields[12]="ResourcesReporting"
        linesrec=data.split('\n')
        for line in linesrec:
            thisTuple=line.split('\t')
            print "thisTuple: %s" % thisTuple
            count=0
            info = {}
            fed_info = {}
            for thisField in thisTuple:
                print "thisField: %s" % thisField
                if(thisField.strip() == ""):
                    continue
                if(count<numcells):
                    info[datafields[count]]=thisField
                    print "info[datafields[%d]]= %s" % (count, thisField)
                    if datafields[count] == 'ResourceGroup':
                        fed_info[datafields[count]] = thisField
                    if datafields[count] == 'FederationName':
                        fed_info[datafields[count]] = thisField
                    if datafields[count] == 'ResourcesReporting':
                        fed_info[datafields[count]] = thisField
                if count<numcells and datafields[count] == 'MeasurementDate' and report_time == None:
                    report_time = thisField
                count=count+1
            if(not info):
                continue
            info['month']=month
            info['year']=year
            apel_data.append(info)
            print "info: %s" % info
            fed_rpt.append(fed_info)
            print "fed_info: %s" % fed_info
        return apel_data, report_time, fed_rpt

    ###########################################################################
    #                            Main   
    ###########################################################################
    def apel_data(self, year=datetime.datetime.now().year, 
            month=datetime.datetime.now().month, **kw):
        data = dict(kw)
        self.user_auth(data)
        self.user_roles(data)
        year = int(year)
        month = int(month)
        try:
            apel_data, report_time, fed_rpt = self.get_apel_data(year, month)
            data['error'] = False
        except (KeyboardInterrupt, SystemExit):
            raise 
        except Exception, e:
            print >> sys.stderr, "Exception occurred while APEL data: %s" % str(e)
            data['title'] = "WLCG Reporting Info Error"
            data['error'] = True
            data['error_message'] = 'Exception occurred while fetching APEL data for <strong>Year:</strong> %s and <strong>Month:</strong> %s <br/></br/><strong>Details:</strong> %s' %(year, month,str(e))
            #raise e
            return data

        ###########################################################################
        # To comply with request to sort by FederationName - 2013Jan24 - wbh
        ###########################################################################
        myApelDict = {}
        for apelRow in apel_data:
            print "apelRow: %s" % apelRow
            myKey = apelRow['FederationName'] + ',' + apelRow['ResourceGroup'] + \
                ',' + apelRow['LCGUserVO']
            myApelDict[myKey] = apelRow
        sortedApel = sorted(myApelDict.iteritems(), key=itemgetter(0))
        myNewApel = []
        for line in sortedApel:
            (myKey, myApelRow) = (line[0], line[1])
            print "myKey = %s" % myKey
            print "myApelRow = %s" % myApelRow
            myNewApel.append(myApelRow)

        ###########################################################################
        # To comply with request to sort by FederationName - 2013Jan24 - wbh
        ###########################################################################
        myFedDict = {}
        for fedRow in fed_rpt:
            print "fedRow: %s" % fedRow
            myKey = fedRow['FederationName'] + ',' + apelRow['ResourceGroup'] + \
                ',' + fedRow['ResourcesReporting']
            myFedDict[myKey] = fedRow
        sortedFed = sorted(myFedDict.iteritems(), key=itemgetter(0))
        myNewFed = []
        for line in sortedFed:
            (myKey, myFedRow) = (line[0], line[1])
            print "myKey = %s" % myKey
            print "myFedRow = %s" % myFedRow
            myNewFed.append(myFedRow)
        data['apel'] = myNewApel
        data['year'] = year
        data['month'] = month 
        data['month_name'] = calendar.month_name[month]
        data['report_time'] = report_time
        data['fedRpt'] = myNewFed
        
        time_info = gratia_interval(year, month)

        #################################################################
        # cpuinfodictionary call     2014Jan22 - wbh
        #################################################################
	hepspecCpuDict,normconstCpuDict = self.getcpuinfodictionary()

        data['title'] = "Reported WLCG data for %s %i" % \
            (calendar.month_name[month], year)

        return data

