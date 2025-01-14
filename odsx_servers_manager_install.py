#!/usr/bin/env python3
# s6.py
#!/usr/bin/python
import os, subprocess, sys, argparse, platform,socket
from scripts.logManager import LogManager
from utils.ods_app_config import readValuefromAppConfig, set_value_in_property_file, readValueByConfigObj, set_value_in_property_file_generic, read_value_in_property_file_generic_section
from colorama import Fore
from utils.ods_scp import scp_upload
from utils.ods_ssh import executeRemoteCommandAndGetOutput,executeRemoteShCommandAndGetOutput, executeShCommandAndGetOutput, executeRemoteCommandAndGetOutputPython36
from utils.ods_cluster_config import config_add_manager_node, config_get_cluster_airgap
from scripts.spinner import Spinner

verboseHandle = LogManager(os.path.basename(__file__))
logger = verboseHandle.logger

class bcolors:
    OK = '\033[92m' #GREEN
    WARNING = '\033[93m' #YELLOW
    FAIL = '\033[91m' #RED
    RESET = '\033[0m' #RESET COLOR

class host_nic_dictionary(dict):
    # __init__ function
    def __init__(self):
        self = dict()

    # Function to add key:value
    def add(self, key, value):
        self[key] = value

host_nic_dict_obj = host_nic_dictionary()

def myCheckArg(args=None):
    parser = argparse.ArgumentParser(description='Script to learn basic argparse')
    parser.add_argument('m', nargs='?')
    parser.add_argument('--host',
                        help='host ip',
                        required='False',
                        default='localhost')
    parser.add_argument('-u', '--user',
                        help='user name',
                        default='root')
    parser.add_argument('-dryrun', '--dryrun',
                        help='Dry run flag',
                        default='false', action='store_true')
    return verboseHandle.checkAndEnableVerbose(parser, sys.argv[1:])

def handleException(e):
    logger.info("handleException()")
    trace = []
    tb = e.__traceback__
    while tb is not None:
        trace.append({
            "filename": tb.tb_frame.f_code.co_filename,
            "name": tb.tb_frame.f_code.co_name,
            "lineno": tb.tb_lineno
        })
        tb = tb.tb_next
    logger.error(str({
        'type': type(e).__name__,
        'message': str(e),
        'trace': trace
    }))
    verboseHandle.printConsoleError((str({
        'type': type(e).__name__,
        'message': str(e),
        'trace': trace
    })))

def getHostConfiguration():
    hostsConfig=""
    hostConfigArray=[]
    hostConfiguration=""
    wantNicAddress=""
    hostsConfig = readValuefromAppConfig("app.manager.hosts")
    logger.info("hostsConfig : "+str(hostsConfig))
    hostConfigArray=hostsConfig.replace('"','').split(",")

    applicativeUserFile = readValuefromAppConfig("app.server.user")
    applicativeUser = str(input(Fore.YELLOW+"Applicative user ["+applicativeUserFile+"]: "+Fore.RESET))
    if(len(str(applicativeUser))==0):
        applicativeUser = str(applicativeUserFile)
    logger.info("Applicative user : "+str(applicativeUser))
    set_value_in_property_file_generic('User',applicativeUser,'install/gs.service','Service')
    set_value_in_property_file_generic('Group',applicativeUser,'install/gs.service','Service')

    if(len(hostsConfig)==2):
        hostsConfig=hostsConfig.replace('"','')
        logger.info("hostsConfig==2 : "+str(hostsConfig))
    if(len(str(hostsConfig))>0):
        logger.info("hostsConfig>0 : "+str(hostsConfig))
        verboseHandle.printConsoleWarning("Current cluster configuration : ["+hostsConfig+"] ")
        hostConfiguration = str(input("press [1] if you want to modify cluster configuration. \nPress [Enter] to continue with current Configuration. : "+Fore.RESET))
        logger.info("hostConfiguration : "+str(hostConfiguration))
        wantNicAddress = str(input(Fore.YELLOW+"Do you want to configure GS_NIC_ADDRESS for host ? [yes (y) / no (n)]: "+Fore.RESET))
        while(len(str(wantNicAddress))==0):
            wantNicAddress = str(input(Fore.YELLOW+"Do you want to configure GS_NIC_ADDRESS for host ? [yes (y) / no (n)]: "+Fore.RESET))
        logger.info("wantNicAddress  : "+str(wantNicAddress))
        if(hostConfiguration != '1'):
            logger.info("hostConfiguration !=1 : "+str(hostConfiguration))
            for host in hostConfigArray:
                logger.info("host  : "+str(host))
                if(wantNicAddress=="yes" or wantNicAddress=="y"):
                    logger.info("wantNicAddress  : "+str(wantNicAddress))
                    gsNICAddress = str(input(Fore.YELLOW+'Enter GS_NIC_ADDRESS for host '+host+" :"+Fore.RESET))
                    while(len(str(gsNICAddress))==0):
                        gsNICAddress = str(input(Fore.YELLOW+'Enter GS_NIC_ADDRESS for host '+host+" :"+Fore.RESET))
                    host_nic_dict_obj.add(host,gsNICAddress)
                    logger.info("host_nic_dict_obj  : "+str(host_nic_dict_obj))
                if(wantNicAddress=="no" or wantNicAddress=="n"):
                    logger.info("wantNicAddress  : "+str(wantNicAddress))
                    gsNICAddress="x"
                    host_nic_dict_obj.add(host,gsNICAddress)
                    logger.info("host_nic_dict_obj  : "+str(host_nic_dict_obj))
    if(len(str(hostsConfig))==0) or (hostConfiguration=='1'):
        gsNicAddress=""
        gsNicAddress1=""
        gsNicAddress2=""
        gsNicAddress3 =""
        managerType = int(input("Enter manager installation type: "+Fore.YELLOW+"\n[1] Single \n[2] Cluster : "+Fore.RESET))
        logger.info("managerType  : "+str(managerType))
        if(managerType==1):
            logger.info("managerType  : "+str(managerType))
            hostsConfig = str(input(Fore.YELLOW+"Enter manager host: "+Fore.RESET))
            while(len(str(hostsConfig))==0):
                hostsConfig = str(input(Fore.YELLOW+"Enter manager host: "+Fore.RESET))
            logger.info("hostsConfig  : "+str(hostsConfig))
            if(len(str(wantNicAddress))==0):
                wantNicAddress = str(input(Fore.YELLOW+"Do you want to configure GS_NIC_ADDRESS for host ? [yes (y) / no (n)]: "+Fore.RESET))
            logger.info("wantNicAddress  : "+str(wantNicAddress))
            if(wantNicAddress=="yes" or wantNicAddress=="y"):
                logger.info("wantNicAddress  Y")
                gsNicAddress = str(input(Fore.YELLOW+'Enter GS_NIC_ADDRESS for host '+hostsConfig+" :"+Fore.RESET))
                logger.info("gsNicAddress  for host "+str(hostsConfig)+ ": "+str(gsNicAddress))
            if(wantNicAddress=="no" or wantNicAddress=="n"):
                logger.info("wantNicAddress  N")
                gsNicAddress="x"
            host_nic_dict_obj.add(hostsConfig,gsNicAddress)
            logger.info("host_nic_dict_obj  : "+str(host_nic_dict_obj))
            if(len(hostsConfig)<=0):
                logger.info("Invalid host. Host configuration is required please specify valid host ip.:"+str(hostsConfig))
                verboseHandle.printConsoleError("Invalid host. Host configuration is required please specify valid host ip.")
                #break
        elif(managerType==2):
            logger.info("managerType==2  : "+str(managerType))
            host1 = str(input(Fore.YELLOW+"Enter manager host1: "+Fore.RESET))
            while(len(str(host1))==0):
                host1 = str(input(Fore.YELLOW+"Enter manager host1: "+Fore.RESET))
            host2 = str(input(Fore.YELLOW+"Enter manager host2: "+Fore.RESET))
            while(len(str(host2))==0):
                host2 = str(input(Fore.YELLOW+"Enter manager host2: "+Fore.RESET))
            host3 = str(input(Fore.YELLOW+"Enter manager host3: "+Fore.RESET))
            while(len(str(host3))==0):
                host3 = str(input(Fore.YELLOW+"Enter manager host3: "+Fore.RESET))
            #wantNicAddress = str(input(Fore.YELLOW+"Do you want to configure GS_NIC_ADDRESS for host ? [yes (y) / no (n)]: "+Fore.RESET))
            logger.info("wantNicAddress  : "+str(wantNicAddress))
            if(wantNicAddress=="yes" or wantNicAddress=="y"):
                logger.info("wantNicAddress  : "+str(wantNicAddress))
                gsNicAddress1 = str(input(Fore.YELLOW+'Enter GS_NIC_ADDRESS for host '+host1+" :"+Fore.RESET))
                while(len(str(gsNicAddress1))==0):
                    gsNicAddress1 = str(input(Fore.YELLOW+'Enter GS_NIC_ADDRESS for host '+host1+" :"+Fore.RESET))
                gsNicAddress2 = str(input(Fore.YELLOW+'Enter GS_NIC_ADDRESS for host '+host2+" :"+Fore.RESET))
                while(len(str(gsNicAddress2))==0):
                    gsNicAddress2 = str(input(Fore.YELLOW+'Enter GS_NIC_ADDRESS for host '+host2+" :"+Fore.RESET))
                gsNicAddress3 = str(input(Fore.YELLOW+'Enter GS_NIC_ADDRESS for host '+host3+" :"+Fore.RESET))
                while(len(str(gsNicAddress3))==0):
                    gsNicAddress3 = str(input(Fore.YELLOW+'Enter GS_NIC_ADDRESS for host '+host3+" :"+Fore.RESET))
            host_nic_dict_obj.add(host1,gsNicAddress1)
            host_nic_dict_obj.add(host2,gsNicAddress2)
            host_nic_dict_obj.add(host3,gsNicAddress3)
            logger.info("host_nic_dict_obj  : "+str(host_nic_dict_obj))
            if(len(host1)<=0 or len(host2)<=0 or len(host3)<=0):
                logger.info("Invalid host. Host configuration is required please specify valid host ip.")
                verboseHandle.printConsoleError("Invalid host. Host configuration is required please specify valid host ip.")
                #break
            hostsConfig=host1+','+host2+','+host3
            logger.info("hostsConfig : "+str(hostsConfig))
        else:
            logger.info("Invalid input host option configuration is required please specify valid host ip.")
            verboseHandle.printConsoleError("Invalid input host option configuration is required please specify valid host ip.")
        if(len(hostsConfig)>0):
            set_value_in_property_file('app.manager.hosts',hostsConfig)
    return hostsConfig

def execute_ssh_server_manager_install(hostsConfig,user):
    hostManager=[]
    gsNicAddress=''
    additionalParam=''
    hostManager=hostsConfig.replace('"','').split(",")
    #print("optionID:"+str(hostsConfig)+" : "+user)
    logger.debug("optionID:"+str(hostsConfig))

    gsOptionExtFromConfig = readValueByConfigObj("app.manager.gsOptionExt")
    #gsOptionExtFromConfig = '"{}"'.format(gsOptionExtFromConfig)
    additionalParam = str(input(Fore.YELLOW+"Enter target directory to install GS [/dbagiga]: "+Fore.RESET))
    gsOptionExt = str(input(Fore.YELLOW+'Enter GS_OPTIONS_EXT  ['+gsOptionExtFromConfig+']: '+Fore.RESET))
    if(len(str(gsOptionExt))==0):
        #gsOptionExt='\"-Dcom.gs.work=/dbagigawork -Dcom.gigaspaces.matrics.config=/dbagiga/gs_config/metrics.xml\"'
        gsOptionExt=gsOptionExtFromConfig
    else:
        set_value_in_property_file('app.manager.gsOptionExt',gsOptionExt)
    gsOptionExt='"\\"{}\\""'.format(gsOptionExt)
    #print("gsoptionext:"+gsOptionExt)

    gsManagerOptionsFromConfig = readValueByConfigObj("app.manager.gsManagerOptions")
    #gsManagerOptionsFromConfig = '"{}"'.format(gsManagerOptionsFromConfig)
    gsManagerOptions = str(input(Fore.YELLOW+'Enter GS_MANAGER_OPTIONS  ['+gsManagerOptionsFromConfig+']: '+Fore.RESET))
    if(len(str(gsManagerOptions))==0):
        #gsManagerOptions="-Dcom.gs.hsqldb.all-metrics-recording.enabled=false"
        gsManagerOptions=gsManagerOptionsFromConfig
    else:
        set_value_in_property_file('app.manager.gsManagerOptions',gsManagerOptions)
    gsManagerOptions='"{}"'.format(gsManagerOptions)

    gsLogsConfigFileFromConfig = readValueByConfigObj("app.manager.gsLogsConfigFile")
    #gsLogsConfigFileFromConfig = '"{}"'.format(gsLogsConfigFileFromConfig)
    gsLogsConfigFile = str(input(Fore.YELLOW+'Enter GS_LOGS_CONFIG_FILE  ['+gsLogsConfigFileFromConfig+']: '+Fore.RESET))
    if(len(str(gsLogsConfigFile))==0):
        #gsLogsConfigFile="/dbagiga/gs_config/xap_logging.properties"
        gsLogsConfigFile=gsLogsConfigFileFromConfig
    else:
        set_value_in_property_file('app.manager.gsLogsConfigFile',gsLogsConfigFile)
    gsLogsConfigFile = '"{}"'.format(gsLogsConfigFile)

    licenseConfig = readValueByConfigObj("app.manager.license")
    #licenseConfig='"{}"'.format(licenseConfig)
    gsLicenseFile = str(input(Fore.YELLOW+'Enter GS_LICENSE ['+licenseConfig+']: '+Fore.RESET))
    if(len(str(gsLicenseFile))==0):
        gsLicenseFile = licenseConfig
    #else:
        #gsLicenseFile = str(gsLicenseFile).replace(";","\;")
    gsLicenseFile='"\\"{}\\""'.format(gsLicenseFile)

    applicativeUser = read_value_in_property_file_generic_section('User','install/gs.service','Service')
    #print("Applicative User: "+str(applicativeUser))

    nofileLimit = str(readValuefromAppConfig("app.user.nofile.limit"))
    nofileLimitFile = str(input(Fore.YELLOW+'Enter user level open file limit : ['+nofileLimit+']: '+Fore.RESET))
    logger.info("hardNofileLimitFile : "+str(nofileLimitFile))
    if(len(str(nofileLimitFile))==0):
        nofileLimitFile = nofileLimit
    #else:
    #    set_value_in_property_file('app.user.hard.nofile',hardNofileLimitFile)
    nofileLimitFile = '"{}"'.format(nofileLimitFile)

    #To Display Summary ::
    '''
    1. Current cluster configuration
    2. GS_NIC_Address configuration
    3. Target Directory
    4. GS_Op_Ext
    5. GS_mgr_op
    6. GS_Log_config
    7. GS_Lic
    8. User_openfile_limit
    '''

    if(len(additionalParam)==0):
        additionalParam= 'true'+' '+'/dbagiga'+' '+hostsConfig+' '+gsOptionExt+' '+gsManagerOptions+' '+gsLogsConfigFile+' '+gsLicenseFile+' '+applicativeUser+' '+nofileLimitFile
    else:
        additionalParam='true'+' '+additionalParam+' '+hostsConfig+' '+hostsConfig+' '+gsOptionExt+' '+gsManagerOptions+' '+gsLogsConfigFile+' '+gsLicenseFile+' '+applicativeUser+' '+nofileLimitFile
    #print('additional param :'+additionalParam)
    logger.debug('additional param :'+additionalParam)
    output=""
    for host in hostManager:
        gsNicAddress = host_nic_dict_obj[host]
        logger.info("NIC address:"+gsNicAddress+" for host "+host)
        if(len(str(gsNicAddress))==0):
            gsNicAddress='x'     # put dummy param to maintain position of arguments
        additionalParam=additionalParam+' '+gsNicAddress
        #print(additionalParam)
        logger.info("Building .tar file : tar -cvf install/install.tar install")
        cmd = 'tar -cvf install/install.tar install'
        with Spinner():
            status = os.system(cmd)
            logger.info("Creating tar file status : "+str(status))
        with Spinner():
            scp_upload(host, user, 'install/install.tar', '')
            scp_upload(host, user, 'install/gs.service', '')
        verboseHandle.printConsoleInfo(output)
        cmd = 'tar -xvf install.tar'
        verboseHandle.printConsoleInfo("Extracting..")
        with Spinner():
            output = executeRemoteCommandAndGetOutput(host, user, cmd)
        logger.info("Extracting .tar file :"+str(output))
        verboseHandle.printConsoleInfo(str(output))

        #Checking Applicative User exist or not
        '''
        cmd = 'id -u '+applicativeUser
        logger.info("cmd : "+cmd)
        verboseHandle.printConsoleInfo("Validating applicative user")
        with Spinner():
            output = executeRemoteCommandAndGetOutputPython36(host, user, cmd)
        #print(output)
        
        if(str(output) == '0'):
            print("exist")
        else:
            print("Not exist")
        logger.info("Validating applicative user :"+str(output))
        verboseHandle.printConsoleInfo(str(output))

        quit()
        '''

        commandToExecute="scripts/servers_manager_install.sh"
        #print(additionalParam)
        logger.debug("Additinal Param:"+additionalParam+" cmdToExec:"+commandToExecute+" Host:"+str(host)+" User:"+str(user))
        with Spinner():
            outputShFile= executeRemoteShCommandAndGetOutput(host, user, additionalParam, commandToExecute)
            #print(outputShFile)
            logger.info("Output : scripts/servers_manager_install.sh :"+str(outputShFile))
        serverHost=''
        try:
            serverHost = socket.gethostbyaddr(host).__getitem__(0)
        except Exception as e:
            serverHost=host
        managerList = config_add_manager_node(host,host,"admin","true")
        logger.info("Installation of manager server "+str(host)+" has been done!")
        verboseHandle.printConsoleInfo("Installation of manager server "+host+" has been done!")

if __name__ == '__main__':
    logger.info("odsx_servers_manager_install")
    verboseHandle.printConsoleWarning('Servers -> Manager -> Install')
    args = []
    menuDrivenFlag='m' # To differentiate between CLI and Menudriven Argument handling help section
    #print('Len : ',len(sys.argv))
    #print('Flag : ',sys.argv[0])
    args.append(sys.argv[0])
    try:
        if len(sys.argv) > 1 and sys.argv[1] != menuDrivenFlag:
            arguments = myCheckArg(sys.argv[1:])
            if(arguments.dryrun==True):
                current_os = platform.system().lower()
                logger.debug("Current OS:"+str(current_os))
                if current_os == "windows":
                    parameter = "-n"
                else:
                    parameter = "-c"
                exit_code = os.system(f"ping {parameter} 1 -w2 {arguments.host} > /dev/null 2>&1")
                if(exit_code == 0):
                    verboseHandle.printConsoleInfo("Connected to server with dryrun mode.!"+arguments.host)
                    logger.debug("Connected to server with dryrun mode.!"+arguments.host)
                else:
                    verboseHandle.printConsoleInfo("Unable to connect to server."+arguments.host)
                    logger.debug("Unable to connect to server.:"+arguments.host)
                quit()
            for arg in sys.argv[1:]:
                args.append(arg)
           # print('install :',args)
        elif(sys.argv[1]==menuDrivenFlag):
            args.append(menuDrivenFlag)
            #host = str(input("Enter your host: "))
            #args.append('--host')
            #args.append(host)
            #user = readValuefromAppConfig("app.server.user")
            user = str(input("Enter your user [root]: "))
            if(len(str(user))==0):
                user="root"
            args.append('-u')
            args.append(user)
        hostsConfig = readValuefromAppConfig("app.manager.hosts")
        args.append('--id')
        hostsConfig=getHostConfiguration()
        args = str(args)
        args =args.replace('[','').replace("'","").replace("]",'').replace(',','').strip()
        args =args+' '+str(hostsConfig)
        logger.debug('Arguments :'+args)
        if(config_get_cluster_airgap):
            execute_ssh_server_manager_install(hostsConfig,user)
        #os.system('python3 scripts/servers_manager_scriptbuilder.py '+args)
        ## Execution script flow diverted to this file hence major changes required and others scripts will going to distrub

    except Exception as e:
        handleException(e)
        logger.error("Invalid argument. "+str(e))
        #verboseHandle.printConsoleError("Invalid argument.")


