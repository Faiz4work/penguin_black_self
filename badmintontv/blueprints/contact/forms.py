from flask_wtf import Form
from wtforms import TextAreaField
from wtforms_components import EmailField
from wtforms.validators import DataRequired, Length


class ContactForm(Form):
    
    email = EmailField(
        validators=[
            DataRequired(),
             Length(3, 254)
        ]
    )
    
    subject = TextAreaField(
        validators=[
            DataRequired(), 
            Length(5, 50)
        ]
    )
    
    text = TextAreaField(
        'Message',
        validators=[
            DataRequired(), 
            Length(1, 8192)
        ]
    )
