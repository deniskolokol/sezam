""" PIA - Public Information Access.
    """

from django.db.models import *
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.vocabulary.models import AuthorityProfile
from apps.backend.models import GenericText, GenericPost, GenericMessage, GenericFile, GenericEvent
from apps.backend.utils import increment_id

PIA_REQUEST_STATUS= (
    ('in_progress', u'In progress'),
    ('successful', u'Successful'),
    ('part_successful', u'Partially successful'),
    ('refused', u'Refused'),
    ('overdue', u'Overdue'),
    ('long_overdue', u'Long overdue'),
    ('no_info', u'Information not held'),
    ('withdrawn', u'Withdrawn by the requester'),
    )


class PIAMessage(GenericMessage):
    """ Class for multitable inheritance by message-like objects related to PIA,
        such as PIARequest and PIAThread.
        """
    def __unicode__(self):
        return 'from: %s; to: %s; subj.: %s' % (self.email_from,
                                                self.email_to, self.subject)


class PIAAttachment(GenericFile):
    """ A file attached to he message in the Thread.
        """
    message= ForeignKey(PIAMessage, related_name='attachments')

    def __unicode__(self):
        return filename


class PIARequest(GenericEvent):
    """ Public Information Access (PIA) request.
        
        Not a container, but a descriptor for the original request from the
        User to the Authority, serves as a reference to the info on Request
        in Threads.
        
        Note: `latest_thread_post` de-normalizes the models' strcture, but
        it is nesessary measure for getting details of the request and its
        last update by one query (as it goes through pagination).
        """
    user= ForeignKey(User, verbose_name=_(u'User'))
    authority= ForeignKey(AuthorityProfile, related_name='authority_requests',
                          verbose_name=_(u'Authority'))
    status= CharField(max_length=50, choices=PIA_REQUEST_STATUS,
        default=PIA_REQUEST_STATUS[0][0], verbose_name=_(u'Request status'))
    latest_thread_post= ForeignKey('PIAThread', null=True, blank=True,
        related_name='latest_thread_post', verbose_name=_(u'latest message'))
    
    def __unicode__(self):
        return "%d: %s" % (self.id, self.summary[:30])


class PIAThread(PIAMessage):
    """ Any message (incoming or outgoing) in the thread following a particular
        Request.
        """
    request= ForeignKey(PIARequest, related_name='thread',
                        verbose_name=_(u'request'))
    is_response= BooleanField(default=True,
                              verbose_name=_(u'Is it a response?'))


class PIAAnnotation(GenericText):
    """ Annotation to a message in the Thread.
        """
    thread_message= ForeignKey(PIAThread, related_name='annotations',
                               verbose_name=_(u'Message'))
    user= ForeignKey(User, verbose_name=_(u'User'))
    created= DateTimeField(auto_now_add=True, verbose_name=_(u'Posted'))


class PIARequestDraft(GenericPost):
    """ A draft of PIA request. Being deleted right after the request is sent.
        
        A draft of the reply to the Authority can also be saved,
        `thread_message` points to the message in the thread, to which the reply
        is intended.
        """
    authority_slug= CharField(max_length=1000,
                              verbose_name=_(u'Recipients (slugs)'))
    user= ForeignKey(User, help_text=_(u'Request from user'))
    lastchanged= DateTimeField(auto_now=True, verbose_name=_(u'Updated'))
    thread_message= OneToOneField(PIAThread, null=True, blank=True,
        default=None, related_name='draft', verbose_name=_(u'Message'))
    
    def __unicode__(self):
        return self.subject[20:]


@receiver(post_save)
def clear_latest_flag(sender, **kwargs):
    """ Filling the latest message in the Thread (see the note on 
        de-normalization in the PIARequest description).
        """
    if sender == PIAThread:
        if kwargs.get('created', False):
            instance= kwargs.get('instance')
            instance.request.latest_thread_post= instance
            instance.request.save()
