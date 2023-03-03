#!/usr/bin/env python3.7
#Migrated to python3

import os, sys, json, boto3, smtplib, yaml, logging, re, time
from datetime import datetime
from optparse import OptionParser
from jira import JIRA
from logging import handlers
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

prog_name = os.path.basename(sys.argv[0])
formatter = logging.Formatter('%(levelname)s: [%(asctime)s] %(message)s', datefmt='%Y-%m-%dT%H:%M:%S%z')
logger = logging.getLogger(__name__)

## Default values
defaults = {
    "econfig": "/home/bin/conf/s3LifeCycleAudit/exclusion.yml",
    "bucketlist": False,
    "config": "/home/bin/conf/s3LifeCycleAudit/s3lcaudit.yml",
    "use_botofile": False,
    "pid_file": "/var/run/%s.pid" % prog_name,
    "log_file": "/var/log/s3LifeCycleAudit.log",
    "log_level": "info",
    "log_backup_count": 5,
    "log_max_bytes": 10*1024*1024,
}

parser = OptionParser()
parser.add_option("-e", "--exclude-config", dest="econfig", default=defaults["econfig"],
                  help="YAML config for exclusion of modules, [default \"%s\"]" % defaults["econfig"])
parser.add_option("-t", "--bucketlist", dest="bucketlist", default=False,
                  help="YAML config containing buckets list as array elements, [default \"%s\"]" % defaults["bucketlist"])
parser.add_option("-c", "--config", dest="config", default=defaults["config"],
                  help="General YAML config for parameters, [default \"%s\"]" % defaults["config"])
parser.add_option("-b", "--use-boto-file", dest="botoFile", action="store_true", default=defaults["use_botofile"],
                  help="This flag will need  ~/.boto or ~/.aws/credentials, [default \"%s\"]" % defaults["use_botofile"])
parser.add_option("--log_backup_count", dest="log_backup_count", type=int, default=defaults["log_backup_count"],
                    help="max number of log file backups to keep [default \"%s\"]" % defaults["log_backup_count"])
parser.add_option("--log_max_bytes", dest="log_max_bytes", type=int, default=defaults["log_max_bytes"],
                    help="max number bytes a log file can have before getting rotated [default \"%s\"]" % defaults["log_max_bytes"])
parser.add_option("-f", "--logfile", dest="log_file", default=defaults["log_file"],
                  help="Logfile path and filename, [default \"%s\"]" % defaults["log_file"])
parser.add_option("-l", "--log-level", dest="log_level", default=defaults["log_level"],
                  help="Set the log level you prefer, [default \"%s\"], accepted ones are 'ERROR', 'DEBUG', 'INFO'" % defaults["log_file"])

(options, args) = parser.parse_args()

## Setting logger handler
if options.log_file == "-":
    logging_handler = logging.StreamHandler()
else:
    logging_handler = handlers.RotatingFileHandler(options.log_file, maxBytes=options.log_max_bytes, backupCount=options.log_backup_count)

logging_handler.setFormatter(formatter)
logger.addHandler(logging_handler)
logger.setLevel(getattr(logging, options.log_level.upper()))

logger.info("==== Starting run for %s ====" %(prog_name))
if options.botoFile:
  try:
    ## Initializing s3 client
    s3 = boto3.client('s3')
  except:
    logger.error("Couldn't find ~/.boto or ~/.aws/credentials, exiting")
    sys.exit(2)
else:
  ## Initializing cred reader
  try:
    sys.path.append('/home/bin/conf')
    import devops_cred_manager_prod
  except:
    logger.error("Unable to find devops_cred_reader module")
    sys.exit(2)

  ## Fetching creds
  ec2_cloudwatch_user = devops_cred_manager_prod.get_cred_file("/home/bin/conf/cred-manager-prod", "aws.credentials.properties")
  accesskey = str(ec2_cloudwatch_user['accessKey'])
  secretkey = str(ec2_cloudwatch_user['secretKey'])

  ## Initializing s3 client
  s3 = boto3.client('s3', aws_access_key_id=accesskey, aws_secret_access_key=secretkey)

if os.path.isfile(options.config):
  logger.info("Reading config")
  config = yaml.safe_load(open(options.config, 'r').read())
  if 'AlertRecipient' in config.keys():
    AlertRecipient = config['AlertRecipient']
  else:
    logger.warning("Couldn't find recipient list in config, will print on STDOUT instead")
    AlertRecipient = False
else:
  logger.error("%s Config not found, will print on STDOUT instead" %(options.config))
  AlertRecipient = False

sleep = 30

## Getting LifeCycle rules for a bucket.
def getModuleLifeCycle(bucket):
  try:
    logger.info("Retrieving policies for bucket %s" %(bucket))
    policies = s3.get_bucket_lifecycle_configuration(Bucket=bucket)
    return policies['Rules']
  except:
    logger.warning("No Lifecycle policy exists OR acess denied for %s" %(bucket))
    return False

# Getting first level modules / folder of a bucket.
def getModuleList(bucket):
  try:
    paginator = s3.get_paginator('list_objects')
    folders = []
    iterator = paginator.paginate(Bucket=bucket, Prefix='', Delimiter='/', PaginationConfig={'PageSize': None})
    logger.info("Getting modules list for %s" %(bucket))
    for response_data in iterator:
      prefixes = response_data.get('CommonPrefixes', [])
      for prefix in prefixes:
        prefix_name = prefix['Prefix']
        if prefix_name.endswith('/'):
          folders.append(prefix_name.rstrip('/'))
    return folders
  except:
    logger.error("Couldn't list objects in %s" %(bucket))
    return False

# Function to check if Bucket level policy exists
def verifyBucketPolicy(policies):
  for rule in policies:
    if 'Status' in rule.keys() and rule['Status'] == 'Enabled':
      if 'Filter' in rule.keys() and 'Prefix' in rule['Filter'].keys():
        policyModule = rule['Filter']['Prefix'].rstrip('/')
      elif 'Prefix' in rule.keys():
        policyModule = rule['Prefix'].rstrip('/')
    if policyModule == '':
      return True
  return False

# Determining modules for which policy is not defined
# and they are not in exclusion list.
def determineNonPolicyModule(modules, policies, excludeModules):
  modules = list(set(modules) - set(excludeModules))
  for rule in policies:
    if 'Status' in rule.keys() and rule['Status'] == 'Enabled':
      if 'Filter' in rule.keys() and 'Prefix' in rule['Filter'].keys():
        policyModule = rule['Filter']['Prefix'].rstrip('/')
      elif 'Prefix' in rule.keys():
        policyModule = rule['Prefix'].rstrip('/')
      if not policyModule:
        modules = []
        break
      elif policyModule in modules:
        modules.remove(policyModule)
  return modules

## Function for sending emails
def sendEmail(attachmentContent, emailBody, recipients, Subject, attachmentName, msgattached=True):
  emailmsg = MIMEMultipart()
  emailmsg['From'] = 'sre-help@company.com'
  emailmsg['To'] = (',').join(recipients)
  emailmsg['Subject'] = Subject
  if msgattached:
    emailmsg.attach(MIMEText("Please find the details and file attached for S3 Buckets / Modules with no policy\n\n%s" %(yaml.safe_dump(emailBody, default_flow_style=False)), 'plain'))
    part = MIMEBase('application', "octet-stream")
    part.set_payload(attachmentContent.encode())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', "attachment; filename=%s" %(attachmentName))
    emailmsg.attach(part)
  else:
    emailmsg.attach(MIMEText("%s" %(yaml.safe_dump(emailBody, default_flow_style=False)), 'plain'))
  email = smtplib.SMTP('localhost:25')
  email.sendmail(emailmsg['From'], recipients, emailmsg.as_string())
  email.quit()

## Function for sending alerts for failed incoming or outgoing files processing.
def sendAlert(noPolicy, recipient):
  Subject = "[no LifeCycle] S3 Bucket: Modules list"
  ## Converting the Dictionary in CSV for emailing as attachment
  if len(noPolicy) >= 1:
    msg = "Bucket,Module\n"
    for b in noPolicy:
      msg = msg + "%s,%s\n" %(b['Bucket'], b['Modules'][0])
      for m in b['Modules'][1:]:
        msg = msg + ",%s\n" %(m)
    if recipient:
      sendEmail(msg, noPolicy, recipient, Subject, "noPolicy-%s.csv" %(datetime.strftime(datetime.now(), "%Y-%m-%d")))
    else:
      print(json.dumps(noPolicy, indent=4))
  else:
    msg = {"All S3 Buckets: Modules have defined policy": ""}
    if recipient:
      sendEmail(None, msg, recipient, Subject, None, False)
    else:
      print(json.dumps(msg, indent=4))

##Reading JIRA credential from cred res base

jira_user_key = devops_cred_manager_prod.get_cred("/home/bin/conf/cred-manager-prod", "atlassian-jira-creds.properties","jira.User")
jira_password_key = devops_cred_manager_prod.get_cred("/home/bin/conf/cred-manager-prod", "atlassian-jira-creds.properties","jira.Password")

##Function to create JIRA tikcet

def create_jira_ticket(noPolicy):
  try:

    jira_url = config['JIRA']['jira_url']
    jira_userid = jira_user_key
    jira_password = jira_password_key
    jira_project_id = config['JIRA']['jira_project_id']
    jira_project_name = config['JIRA']['jira_project_name']
    issue_summary = config['JIRA']['issue_summary']
    issue_assignee = config['JIRA']['assignee']
    jira_description =  config['JIRA']['description'] + '\n' + '\n' + yaml.dump_all(noPolicy, explicit_start=True)
    issue_dict = {'project':{'id':jira_project_id}, 'summary': issue_summary, 'description': jira_description, 'issuetype':{'name':'Bug'}}
    jira = JIRA(jira_url, basic_auth=(jira_userid, jira_password))
    new_issues = jira.create_issue(fields=issue_dict)
    return True

  except Exception as e:
   logger.error("Couldn’t file Jira ticket\nError: %s" %(str(e)))
   return False


def getBucketList():
  logger.info("Getting bucket list")
  buckets = s3.list_buckets()['Buckets']
  bucketList = []
  for b in buckets:
    bucketList.append(b['Name'])
  return bucketList

def main():
  # Reading exclusion conf and ingesting values.
  if os.path.isfile(options.econfig):
    logger.info("Reading exception list %s" %(options.econfig))
    exceptionList = yaml.safe_load(open(options.econfig, 'r').read())
    if not exceptionList:
      exceptionList = []
  else:
    exceptionList = []
    logger.error("Couldn't read %s, no exclusions" %(options.econfig))

  # Reading bucket conf if available and has values.
  if options.bucketlist:
    if os.path.isfile(options.bucketlist):
      logger.info("Reading conf file to scan buckets %s" %(options.bucketlist))
      bucketList = yaml.safe_load(open(options.bucketlist, 'r').read())
      if not bucketList:
        bucketList = False
    else:
      bucketList = False
      logger.error("%s file is not readable" %(options.bucketlist))
  else:
    bucketList = False

  # Getting Bucket list of not provided.
  if not bucketList:
    bucketList = getBucketList()

  # Starting to iterate through buckets and finding modules with not policies.
  noPolicy = []
  for bucket in bucketList:
    excludeModules = []
    for e in exceptionList:
      if e['Bucket'] == bucket:
        if 'Bucket' in e.keys() and 'Modules' in e.keys():
          excludeModules = e['Modules']
          break
        else:
          logger.error("Error reading %s" %e)
          break
    if len(excludeModules) == 1 and excludeModules[0] == "/":
      logger.info("skipping %s, it is in exception list" %(bucket))
      continue
    modules = getModuleList(bucket)
    if type(modules) == list and len(modules) == 0:
      policies = getModuleLifeCycle(bucket)
      if not verifyBucketPolicy(policies):
        noPolicy.append({'Bucket': bucket, 'Modules': ["NO Modules found for s3://%s and no whole bucket policy" %(bucket)]})
      else:
        continue
    elif not modules:
      noPolicy.append({'Bucket': bucket, 'Modules': ["Access Denied for listing s3://%s" %(bucket)]})
      continue
    policies = getModuleLifeCycle(bucket)
    if policies:
      logger.info("Starting to verify LifeCycle policy for %s" %(bucket))
      noPolicyModules = determineNonPolicyModule(modules, policies, excludeModules)
      if len(noPolicyModules) >= 1:
        noPolicy.append({'Bucket': bucket, 'Modules': noPolicyModules})
    else:
      noPolicy.append({"Bucket": bucket, "Modules": ["NO LIFECYCLE POLICY defined for s3://%s" %(bucket)]})
    # Sleeping for "sleep" sec before calling next bucket, to avoid throttling by AWS
    time.sleep(sleep)

  # Sending Alert whether nopolicy modules are found or not
  logger.info("Sending email for Buckets/Modules with no policy found")
  sendAlert(noPolicy, AlertRecipient)
  logger.info("Creating JIRA ticket")
  if create_jira_ticket(noPolicy):
    logger.info("JIRA ticket is created")

  logger.info("==== Run is complete, exiting ====")

if __name__ == '__main__':
  main()
