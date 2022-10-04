from flask_babel import lazy_gettext as _
from flask_wtf import Form
from wtforms import StringField, HiddenField
from wtforms.validators import DataRequired, Optional, Length


class CreditCardForm(Form):
    
    # This is targetted by JS to submit the publishable key to Stripe
    stripe_key = HiddenField(
        _('Stripe publishable key'),
        validators=[
            DataRequired(), 
            Length(1, 254)
        ]
    )
    
    # Plan ID
    id = HiddenField(
        _('Plan ID'),
        validators=[
            DataRequired(), 
            Length(1, 254)
        ]
    )

    # Name 
    name = StringField(
        _('Name on card'),
        validators=[
            DataRequired(), 
            Length(1, 254)
        ]
    )


class UpdateSubscriptionForm(Form):
    pass


class CancelSubscriptionForm(Form):
    pass
