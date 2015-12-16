# -*- coding: utf-8 -*-
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.header import Header
import urlparse
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import uuid
from ckan import model
from ckan.lib.celery_app import celery
import logging

log = logging.getLogger(__name__)

@celery.task(name = "notifications.followdataset")
def followdataset(user_id, dataset_id):
    logging.warn("follow")
    toolkit.get_action('follow_dataset')(context = {'user' : user_id, 'model' : model, 'session' : model.Session}, data_dict={'id' : dataset_id}) 

def _send_mail(sender, sender_name, receiver, receiver_name, subject, message, mailserver):
    msg = MIMEMultipart()
    msg['From'] = "%s <%s>" % (sender_name, sender)
    recipient = u"%s <%s>" % (receiver_name, receiver)
    msg['To'] = Header(recipient, 'utf-8')
    subject = Header(subject.encode('utf-8'), 'utf-8')
    msg['Subject'] = subject
    msg.attach(MIMEText(message.encode('utf-8'), 'plain', 'utf-8'))
    try:
        mailserver.sendmail(sender, receiver, msg.as_string())
    except smtplib.SMTPException, e:
        log.exception(e)

@celery.task(name = "notifications.send")
def send_notifications(context, data_dict):
    log.info('smtp server port: %s', context['smtp_server_port'])
    log.info('smtp server port type: %s', type(context['smtp_server_port']))
    mailserver = smtplib.SMTP(str(context['smtp_server']), str(context['smtp_server_port']))
    mailserver.ehlo()
    sender = context['mail_from']
    sender_name = context['mail_from_name']
    subject = u'Notifikácia: {action} {name} ({id})'
    subject = subject.format(action = data_dict['entity_action'], name = data_dict['entity_name'], id = data_dict['entity_id'])
    message = u'''
Dobrý deň {name},
oznamujeme Vám, že bol {action} {entity_name} ({entity_id}).
V systéme MOD je dostupný na URL adrese: {url} .

Tento email Vám bol vygenerovaný automaticky, preto naň, prosím, neodpisujte.
   
{signature}
'''
    url = urlparse.urljoin(context['site_url'], data_dict['entity_url'])
    recipients = data_dict['recipients']
    log.info('recipients without duplicates: %s', recipients)
    sended = []
    for recipient in recipients:
        if recipient in sended:
            continue
        sended.append(recipient)
        message = message.format(name=recipient[1], action = data_dict['entity_action'], entity_name = data_dict['entity_name'], entity_id = data_dict['entity_id'], url = url, signature = sender_name)
        _send_mail(sender, sender_name, recipient[0], recipient[1], subject, message, mailserver)
    mailserver.quit()
    
    
@celery.task(name = "notifications.general.send")
def send_general_notifications(context, data_dict):
    log.info('smtp server port: %s', context['smtp_server_port'])
    log.info('smtp server port type: %s', type(context['smtp_server_port']))
    mailserver = smtplib.SMTP(str(context['smtp_server']), str(context['smtp_server_port']))
    mailserver.ehlo()
    sender = context['mail_from']
    sender_name = context['mail_from_name']
    subject = data_dict['subject']
    message = data_dict['message']
    recipients = data_dict['recipients']
    sended = []
    for recipient in recipients:
        if recipient in sended:
            continue
        sended.append(recipient)
        _send_mail(sender, sender_name, recipient[0], recipient[1], subject, message.format(name = recipient[1], signature = sender_name), mailserver)
    mailserver.quit()