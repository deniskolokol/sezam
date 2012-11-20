from django.utils.translation import ugettext_lazy as _
from django import forms

REQUEST_BODY_TEMPLATE= _(u"Dear %(name)s, %(space3)sYours faithfully, %(space1)s%(user_name)s")
SPACER="""
"""

class MakeRequestForm(forms.Form):
    authority_name= forms.CharField(
        required=False, # It IS (of course) required, but it's checked elsewhere.
        label=_(u'You are sending a request to'),
        widget=forms.TextInput(
            attrs={
                'class': 'span',
                'readonly': '',
                'style': 'display: none;'
                }
            )
        )
    authority_slug= forms.CharField(
        required=False, # It IS (of course) required, but it's checked elsewhere.
        widget=forms.TextInput(
            attrs={
                'class': 'span',
                'readonly': '',
                'style': 'display: none;'
                }
            )
        )
    request_subject= forms.CharField(
        required=False,
        label=_(u'Request summary'),
        widget=forms.TextInput(
            attrs={
                'class': 'span5',
                'placeholder': _(u'Subject')
                }
            )
        )
    request_body= forms.CharField(
        label=_(u'Your request'),
        widget=forms.Textarea(
            attrs={
                'class': 'span4'
                }
            ),
        )

    def __init__(self, *args, **kwargs):
        initial= kwargs.pop('initial', None)
        super(MakeRequestForm, self).__init__(*args, **kwargs)
        if initial:
            try:
                self.fields['request_body'].initial= initial['request_body']
                self.fields['request_subject'].initial= initial['request_subject']
            except KeyError:
                self.fields['request_body'].initial= REQUEST_BODY_TEMPLATE % {
                    'name': initial['authority_name'],
                    'user_name': initial['user_name'],
                    'space3': SPACER*3, 'space1': SPACER}
                self.fields['request_subject'].initial= ''
            self.fields['authority_name'].initial= initial['authority_name']
            self.fields['authority_slug'].initial= initial['authority_slug']
        else:
            self.fields['request_body'].initial= REQUEST_BODY_TEMPLATE % {
                'name': ' ', 'user_name': ' ', 'space3': SPACER*3, 'space1': SPACER}
            self.fields['request_subject'].initial= ''
            self.fields['authority_name'].initial= ''
            self.fields['authority_slug'].initial= ''