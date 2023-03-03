#!/usr/bin/env python3.7
import boto3
import datetime
from datetime import date
from jira import JIRA
import configparser
import sys

try:
        sys.path.append("/home/bin/conf")
        import devops_cred_manager
except Exception as e:
 print (str(e))
 exit(1)

iam = boto3.client('iam')
config = configparser.ConfigParser()
headless_users_list = dict()

def get_user_keys():
    try:
        users_dict = iam.list_users()
        jira_url = get_config_details('JIRA', 'jira_url')
        print(("Jira Url : " , jira_url))
        if (users_dict["IsTruncated"]):
            print ("Response truncated while fetching the users list")
        else:
            for user_details in users_dict["Users"]:
                userName = user_details['UserName']
                userId = user_details['UserId']
                print((user_details.get('PasswordLastUsed')))
                password_last_used(userName, user_details)
                key_details = iam.list_access_keys(UserName = userName)
                accessKey_metaData = key_details['AccessKeyMetadata']
                if (len(accessKey_metaData) > 0):
                    for metaData in accessKey_metaData:
                        if (metaData.get('Status') == 'Active'):
                            userName = metaData.get('UserName')
                            status = metaData.get('Status')
                            accesskey_create_date = metaData.get('CreateDate')
                            accessKeyId = metaData.get('AccessKeyId')
                            accessKeyLastUsed = iam.get_access_key_last_used(AccessKeyId = accessKeyId)
                            print(("UserName: ", userName , "AccessKeyId: " , accessKeyId, " Status: ", status , " AccessKeyLastUsed:  ", accessKeyLastUsed.get('AccessKeyLastUsed').get('LastUsedDate'), " Last used Service Name: ", accessKeyLastUsed.get('AccessKeyLastUsed').get('ServiceName')))
                            check_accesskey_age(accesskey_create_date, userName)
                        else:
                            print("User ", userName ," key ", accessKeyId ," is not active")

    except Exception as e:
                print("Exception raised while fetching the user details:", (str(e)))


def check_accesskey_age(accesskey_create_date, userName):
    try:
        print("Checking user ", userName ," access key age")
        days_diff = date_diff(accesskey_create_date)
        rotation_period = 0
        exists = 1
        issue_summary_desc = ""
        if(check_user(userName, "accesskey_excluding")):
            print("User ", userName ," in accesskey excluding list")
            exists = 0
        elif(check_user(userName, "headless_user")):
            rotation_period = int(get_config_details('rotation_period','headless_users_rotation_period'))
            issue_summary = str(get_config_details('JIRA','pwdlogin_summary'))
            issue_description = str(get_config_details('JIRA','pwdlogin_description'))
            print(("Headless user: ", userName, "Rotation period: ", rotation_period, " Days difference :", days_diff))
            exists = 1
        else:
            rotation_period = int(get_config_details('rotation_period','users_accesskey_rotation_period'))
            issue_summary = str(get_config_details('JIRA','accesskey_summary'))
            issue_description = str(get_config_details('JIRA','accesskey_description'))
            print(("Normal user: ", userName, "Rotation period: ", rotation_period, " Days difference :", days_diff))
            exists = 1

        print ("Validating expiry days...")

        if(days_diff >= rotation_period and exists == 1):
            print ("Before creating Jira ticket..")
            if(get_config_details('JIRA', 'create_jira_tickets') == '1'):
                create_jira_ticket(userName, issue_summary, issue_description)
        else:
            print ("No need to rotate keys as his keys age is lessthan the rotation period time..")
    except Exception as e:
                print("Exception raised while checking the accesskey age: ", (str(e)))

def date_diff(date_field):
    try:
        days_difference  = date.today() - date(date_field.year, date_field.month, date_field.day)
        return days_difference.days
    except Exception as e:
                print("Exception while finding the date difference:  ", (str(e)))

def password_last_used(userName, user_details):
    try:
        
        print("Checking user ", userName ," password last used date and time")
        if(check_user(userName, "pwd_use_excluding")):
            print("User ", userName ," is headlessuser and can't be verified last console login(pwd use)")
        else:
            console_access_users_str = get_config_details('console_access_users_list','console_users')
            console_access_users_list_obj = console_access_users_str.split(", ")
            if(userName in console_access_users_list_obj):
                print(("Control in password_last_used...", userName))
                creds_last_used_date = user_details['PasswordLastUsed']
                unused_days_diff = date_diff(creds_last_used_date)
                pwd_unused_days = int(get_config_details('rotation_period','pwd_unused_days'))
                print(("PWD Unused days config: ", pwd_unused_days , " Days difference: " , unused_days_diff))
                if (unused_days_diff >= pwd_unused_days):
                    pwd_issue_summary = str(get_config_details('JIRA','pwdlogin_summary'))
                    pwd_issue_description = str(get_config_details('JIRA','pwdlogin_description'))
                    if(get_config_details('JIRA','create_jira_tickets') == '1'):
                        print(("Creating ticket as password used a while ago (", pwd_unused_days ," days)"))
                        create_jira_ticket(userName, pwd_issue_summary, pwd_issue_description)
    except Exception as e:
                print("Exception occurred while checking the password last used condition: ", (str(e)))


def check_user(userName, condition_str):
    try:
        if(condition_str == 'headless_user'):
            list_of_users = get_config_details('headless_users','headless_users_list')
        elif(condition_str == 'accesskey_excluding'):
            list_of_users = get_config_details('accesskey_excluding_list','accesskey_excluding_list')
        elif(condition_str == 'pwd_use_excluding'):
            list_of_users = get_config_details('console_access_excluding_list','pws_use_excluding_list')
        else:
            list_of_users = ''
        users_list_obj = list_of_users.split(", ")
        if (userName in users_list_obj):
            print((userName, " is in ",condition_str, " list ",  users_list_obj))
            return True
        else:
            print((userName, " is not in ", condition_str , " list"))
            return False
    except Exception as e:
                print("Exception occurred while checking the headless user: ", (str(e)))


def create_jira_ticket(userName, issue_summary, issue_description):
    try:
        print ("Control in create Jira ticket function..")
        jira_url = str(get_config_details('JIRA','jira_url'))
        jira_userid = devops_cred_manager.get_cred("/home/bin/conf/creds_pkg", "atlassian-jira-creds.properties","jira.User")
        jira_password = devops_cred_manager.get_cred("/home/bin/conf/creds_pkg", "atlassian-jira-creds.properties","jira.Password")
        jira_project_id = int(get_config_details('JIRA', 'jira_project_id'))
        jira_project_component_name = str(get_config_details('JIRA', 'jira_project_component_name'))
        issue_dict = {'project':{'id':jira_project_id},'components':[{'name':jira_project_component_name},],'summary': userName + " - " +issue_summary, 'description': issue_description, 'issuetype':{'name':'Bug'},}
        print(("Jira ticket details: ", issue_dict))
        jira = JIRA(jira_url, basic_auth=(jira_userid, jira_password))
        print ("Before creating jira tickets...")
        new_issues = jira.create_issue(fields=issue_dict)
        print(("Jira ticket has been created: ", new_issues))
    except Exception as exp:
        print("Exception while creating jira ticket ", str(exp))
        print("Error code: ", (str(e)))

def load_config():
    try:
        print ("Loading configuration..")
        config.read("iam_conf.ini")
    except Exception as e:
                print("Exception occurred while loading the configuration file : ", (str(e)))
def get_config_details(section_name, key):
        try:
                return config.get(section_name,key)
        except Exception as e:
                print("Requested element doesn't exists : ", (str(e)))

def main():
    try:
        print ("Started..")
        load_config()
        get_user_keys()

    except Exception as exp:
                print("Exception occurred while reading configuration file: ", (str(e)))
                print (exp)
main()

