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
    ('in_progress', _(u'In progress')),
    ('successful', _(u'Successful')),
    ('part_successful', _(u'Partially successful')),
    ('refused', _(u'Refused')),
    ('overdue', _(u'Overdue')),
    ('long_overdue', _(u'Long overdue')),
    ('no_info', _(u'Information not held')),
    ('withdrawn', _(u'Withdrawn by the requester')),
    ('awaiting', _(u'Awaiting classification'))
    )

def get_request_status(status='in_progress'):
    """
    Simply return the proper element to fill the status of the PIARequest.
    """
    try:
        status_index= [i[0] for i in PIA_REQUEST_STATUS].index(status)
    except: # The most neutral 'in_progress'.
        status_index= 0
    return PIA_REQUEST_STATUS[status_index][0]


class PIAMessage(GenericMessage):
    """
    Class for multitable inheritance by message-like objects related to PIA,
    such as PIARequest and PIAThread.
    """
    def __unicode__(self):
        return 'from: %s; to: %s; subj.: %s' % (self.email_from,
                                                self.email_to, self.subject)


class PIAAttachment(GenericFile):
    """
    A file attached to he message in the Thread.
    """
    message= ForeignKey(PIAMessage, related_name='attachments')

    def __unicode__(self):
        return self.filename


class PIARequest(GenericEvent):
    """
    Public Information Access (PIA) request.

    Not a container, but a descriptor for the original request from the
    User to the Authority, serves as a reference to the info on Request
    in Threads.

    Note: `latest_thread_post` de-normalizes the models' structure, but
    it is a nesessary measure for getting details of the request and its
    last update in one query (as it goes through pagination).
    """
    user= ForeignKey(User, related_name='requests_made',
                     verbose_name=_(u'User'))
    authority= ForeignKey(AuthorityProfile, related_name='authority_requests',
                          verbose_name=_(u'Authority'))
    status= CharField(max_length=50, choices=PIA_REQUEST_STATUS,
        default=PIA_REQUEST_STATUS[0][0], verbose_name=_(u'Request status'))
    latest_thread_post= ForeignKey('PIAThread', null=True, blank=True,
        related_name='latest_thread_post', verbose_name=_(u'latest message'))
    
    def __unicode__(self):
        return "%d: %s" % (self.id, self.summary[:30])


class PIAThread(PIAMessage):
    """
    Any message (incoming or outgoing) in the thread following
    a particular Request.
    """
    request= ForeignKey(PIARequest, related_name='thread',
                        verbose_name=_(u'request'))
    is_response= BooleanField(default=True,
                              verbose_name=_(u'Is it a response?'))

    def __unicode__(self):
        return "%s (request %d)" % (self.subject[:50], self.request.id)


class PIAAnnotation(GenericText):
    """
    Annotation to a message in the Thread.
    """
    thread_message= ForeignKey(PIAThread, related_name='annotations',
                               verbose_name=_(u'Message'))
    user= ForeignKey(User, verbose_name=_(u'User'))
    created= DateTimeField(auto_now_add=True, verbose_name=_(u'Posted'))


class PIARequestDraft(PIAMessage):
    """
    A draft of PIA request. Being deleted right after the request is sent.

    There are 2 kinds of Drafts:
    * A draft that initiates the Request.
    This has `thread_message` = null and can be linked to several Authorities.

    * A draft that is a response to the message from Authority (or a draft
    of the reply from Authority, received by snail mail, and being entered
    to the system by User manually).
    In those drafts `thread_message` should point to the message in the Thread,
    on which it is a reply, and should _always_ have a link to the specified
    Authority - the one from the message the Draft is pointing to.
    """
    authority= ManyToManyField(AuthorityProfile,
                               verbose_name=_(u'Authority(ies)'))
    user= ForeignKey(User, help_text=_(u'Request from user'))
    lastchanged= DateTimeField(auto_now=True, verbose_name=_(u'Updated'))
    thread_message= OneToOneField(PIAThread, null=True, blank=True,
        default=None, related_name='draft', verbose_name=_(u'Message'))

    def fill_authority(self, authority=None, **kwargs):
        """
        Re-filll the list of authorities in the draft.
        """
        if authority:
            self.authority.clear()
            if not isinstance(authority, list):
                authority= list(authority)
                for auth in authority:
                    self.authority.add(auth)

    def __unicode__(self):
        return self.subject


@receiver(post_save)
def clear_latest_flag(sender, **kwargs):
    """
    Filling the latest message in the Thread (see the note on 
    de-normalization in the PIARequest description).
    """
    if sender == PIAThread:
        if kwargs.get('created', False):
            instance= kwargs.get('instance')
            instance.request.latest_thread_post= instance
            instance.request.save()
