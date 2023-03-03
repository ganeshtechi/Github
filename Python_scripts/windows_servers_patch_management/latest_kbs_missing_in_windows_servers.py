#!/usr/bin/env python3

import boto3, datetime, yaml, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

client = boto3.client('ssm', region_name='us-east-1')

file = "/home/bin/conf/windows_kbs_conf/config.yml"
config = yaml.safe_load(open(file, 'r').read())
filter_days = config['kb_release_days']['days']

today_date = datetime.date.today()
filter_days = config['kb_release_days']['days']
time_delt = datetime.timedelta(days = filter_days)
final_date = today_date - time_delt
last_week_days = today_date - final_date


def get_patches():
	try:
		print ("Fetching patch information..")
		responses_list = []
		response = client.describe_available_patches()
		results = response["Patches"]
		while "NextToken" in response:
			response = client.describe_available_patches(NextToken=response["NextToken"])
			results.extend(response["Patches"])
			config_severity = config['Fitler_status']['MsrcSeverity']			
			for i in response['Patches']:
				if i['MsrcSeverity'] == config_severity:
					date_time_obj = datetime.datetime.strptime(str(i['ReleaseDate']), '%Y-%m-%d %H:%M:%S%z')
					output_days = today_date - date_time_obj.date()
					if output_days < last_week_days:
						responses_list.append(i)
		print ("Completed fetching patch information..")
		return responses_list
	except Exception as e:
		print(str(e))

def get_instance_name(fid):
	""" When given an instance ID as str e.g. 'i-1234567', return the instance 'Name' from the name tag.. This is called in the above function to get instacne names """
	try:
		# When given an instance ID as str e.g. 'i-1234567', return the instance 'Name' from the name tag.
		ec2 = boto3.resource('ec2', region_name = "us-east-1")
		ec2instance = ec2.Instance(fid)
		instancename = ''
		for tags in ec2instance.tags:
			if tags["Key"] == 'Name':
				instancename = tags["Value"]
		return instancename
	except Exception as exp:
		logger.error("Exception occurred while fetching EC2 instance names")



def get_instance_pathes(Instanceid):
        dict = {}
        paginator = client.get_paginator('describe_instance_patches')
        page_iterator = paginator.paginate(InstanceId=Instanceid, Filters=[{'Key': 'State','Values': ["Missing"]}])
        for page in page_iterator:
              for patch in page['Patches']:
                    mylist = []
                    if patch['KBId'] not in mylist:
                          instance_name = get_instance_name(Instanceid)
                          mylist.append(Instanceid +"(" +instance_name+ ")")
                          dict[patch['KBId']] = mylist
                    else:
                          dict[patch['KBId']].append(Instanceid)
        return dict

def list_ssm_inventory():
        instances_list = []
        response = client.get_inventory()
        for instance_id in response['Entities']:
                instances_list.append(instance_id['Id'])
        print(instances_list)
        return instances_list

def filter_func(res_ele):
	try:
		dict1 = config['Filter']
		for filter in dict1:
			if filter in res_ele:
				for item in dict1[filter]:
					if item == res_ele[filter]:
						return True
	except Exception as e:
		print(str(e))

def mail_header_message():
	try:
		header_message = ""
		header_message += "<html><head><style> table { border-collapse: collapse;} table, td, th { border: 1px solid black;}</style></head><body>"
		
		return header_message
	except Exception as e:
		print("Exception while constructing mail message header: ", (str(e)))

def mail_footer_message():
	try:
		footer_message = ""
		footer_message += "</body></html>"
		
		return footer_message
	except Exception as e:
		print("Exception while constructing mail footer message: ", (str(e)))

def construct_email_message(kbinfo, ssm_kb_info):
	try:
		mail_message = ""
		if len(kbinfo) > 0:
			header_message = "Recent released KBs in last {} days".format(filter_days)
		
			mail_message += "<h3>" + header_message + "</h3><br> <table border=1> <tr bgcolor='#81DAF5'><th>KB Id</th><th>Product</th><th>ReleaseDate</th><th>Title</th><th>MsrcSeverity</th><th>Instance_Ids</th></tr>"
			for obj in kbinfo:
				mail_message += "<tr bgcolor='#F5DA81'><td align=center> <a href=https://www.catalog.update.microsoft.com/Search.aspx?q=" + obj['KbNumber'] + ">" +obj['KbNumber']+ "</a></td>"
				mail_message += "<td align=center>" +obj['Product']+ "</td>"
				mail_message += "<td align=center>" +obj['ReleaseDate']+ "</td>"
				mail_message += "<td align=center>" +obj['Title']+ "</td>"
				mail_message += "<td align=center>" +obj['MsrcSeverity']+ "</td>"
				if obj['KbNumber'] in ssm_kb_info:
					str_Instance_Ids = ''.join(map(str, ssm_kb_info.get(obj['KbNumber'])))
					mail_message += "<td align=center>" + str_Instance_Ids + "</td></tr>"
				else:
					mail_message += "<td align=center> - </td></tr>"
			mail_message +="</table>"
		else:
			print ("in Else condition..")
			header_message = "<h2>There are no latest kbs found in last {} days!</h2>".format(filter_days)
			mail_message = "<h3>" + header_message + "</h3><br>"
		return mail_message
	except Exception as e:
		print("Exception while constructing mail message in function construct_email_message: ", (str(e)))


def construct_other_mail_body_message(sys_manager_kb_info):
	try:
		if len(sys_manager_kb_info) > 0:
			#print("starting of construct_other_mail_body_message..")
			mail_body = "<h2>Below are the list of kbs missing from SSM managed instances</h2>"
			mail_body += "<table border=1> <tr bgcolor='#81DAF5'><th>KB Id</th><th>Instance_Id</th><th>Host Name</th></tr>"
			#print("Before for loop in construct_other_mail_body_message..")
			for kb_entry in sys_manager_kb_info:
				#print("Befor finding the length..")
				instances_count = len(sys_manager_kb_info[kb_entry])
				num_of_instances = str(instances_count+1)
				#print("Length..", num_of_instances)
				
				mail_body += "<tr><td rowspan = " + num_of_instances + "> <a href= https://www.catalog.update.microsoft.com/Search.aspx?q=" + kb_entry + ">" + kb_entry + "</a></td><td></td><td></td></tr>"
				#print("Before instance entry for loop..")
				for instance_entry in sys_manager_kb_info[kb_entry]:
					split_str = instance_entry.split("(")
					mail_body += "<tr><td>" + split_str[0] + "</td>"
					mail_body += "<td>" + split_str[1][:len(split_str[1])-1] + "</td></tr>"
			mail_body += "</table>"
			#print(mail_body)
		else:
			mail_body = "<h2>All SSM managed instances are up to date and no missing KBs to report! </h2>"
		return mail_body
	except Exception as e:
		print("Exception while constructing other mail body message: ", (str(e)))

def send_email_report(email_body):
	try:
		msg = MIMEMultipart()
		msg['From'] = 'sre-help@company.com'
		recipients = config['AlertRecipient']
		msg['To'] = (',').join(recipients)
		msg['Subject'] = "Recently released kbs"
		msg.attach(MIMEText(email_body, 'html'))
		email = smtplib.SMTP('localhost:25')
		mail_response_msg = email.sendmail(msg['From'], msg['To'], msg.as_string())
		email.quit()
		print ("E-mail has been sent.")
	except Exception as exp:
		print ("Exception occurred while sending e-mail notification: ", str(exp))

def get_recently_released_kbs():
	try:
		print ("Fetching recently released KBs")
		findings_list = []
		kb_instances_dict = {}
		get_patch_list = get_patches()
		for ele in get_patch_list:
			findings_dict = {}
			if filter_func(ele) == True:
				findings_dict['KbNumber'] = ele['KbNumber']
				findings_dict['Product'] = ele['Product']
				findings_dict['ReleaseDate'] = str(ele['ReleaseDate'])
				findings_dict['Title'] = ele['Title']
				findings_dict['MsrcSeverity'] = ele['MsrcSeverity']
				findings_list.append(findings_dict)
		return findings_list
	except Exception as e:
		print("Exception while fetching the recently released KBs: ", (str(e)))


def get_missing_kbs_from_ssm_managed_instances():
	try:
		print ("Fetching missing KBs from SSM managed instances..")
		all_kb_list = []
		sys_manager_kb_info = {}
		print ("listing ssm inventory...")
		for instances in list_ssm_inventory():
			all_kb_list.append(get_instance_pathes(instances))
		print ("Listing all KBs")
		for dict in all_kb_list:
			for list in dict:
				if list in sys_manager_kb_info:
					sys_manager_kb_info[list] += (dict[list])
				else:
					sys_manager_kb_info[list] = dict[list]
		return sys_manager_kb_info
	except Exception as e:
		print("Exception while fetching missing kbs related to ssm managed instances: ", (str(e)))



def main():
	try:
		findings_list = get_recently_released_kbs()
		sys_manager_kb_info = get_missing_kbs_from_ssm_managed_instances()
		print ("Constructing mail message ...")	
		mail_message_body = ""
		mail_message_body = mail_header_message()
		mail_message_body += construct_email_message(findings_list, sys_manager_kb_info)
		mail_message_body += construct_other_mail_body_message(sys_manager_kb_info)
		mail_message_body += mail_footer_message()
		#print ("Final Mail Message: " , mail_message_body)
		send_email_report(mail_message_body)
	except Exception as e:
		print("Exception while executing the main method: ", (str(e)))       
main()
