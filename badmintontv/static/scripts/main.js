// A super basic inflection library to pluralize words.
// Updates drop-down text based on number of selected items 
var pluralize = function(word, count) {

    if (count === 1) {
        return word;
    }

    return word + 's';
};

// Format datetimes in multiple ways, depending on which CSS class is set on it
var momentjsClasses = function() {

    var $fromNow = $('.from-now');
    var $shortDate = $('.short-date');

    // Show relative time  with `momentjs` 
    $fromNow.each(function(i, e) {
        (function updateTime() {
            var time = moment($(e).data('datetime'));
            $(e).text(time.fromNow());
            $(e).attr('title', time.format('MMMM Do YYYY, h:mm:ss a Z'));
            setTimeout(updateTime, 1000);
        })();
    });

    // Show short-form date with `momentjs` 
    $shortDate.each(function(i, e) {
        var time = moment($(e).data('datetime'));
        $(e).text(time.format('MMM Do YYYY'));
        $(e).attr('title', time.format('MMMM Do YYYY, h:mm:ss a Z'));
    });
};

// Bulk delete items
var bulkDelete = function() {

    // J-Query selectors 
    var selectAll = '#select_all';
    var checkedItems = '.checkbox-item';
    var colheader = '.col-header';
    var selectedRow = 'warning';
    var updateScope = '#scope';
    var bulkActions = '#bulk_actions';

    $('body').on('change', checkedItems, function() {

        // J-Query selector for all checked items 
        var checkedSelector = checkedItems + ':checked';

        // Number of checked items 
        var itemCount = $(checkedSelector).length;

        // Grammar: Pluralize 'item' --> 'items'
        var pluralizeItem = pluralize('item', itemCount);

        // Text for drop-down box
        var scopeOptionText = itemCount + ' selected ' + pluralizeItem;

        // If checked
        if ($(this).is(':checked')) {

            // Add/Remove a CSS class to each row 
            $(this).closest('tr').addClass(selectedRow);

            // Hide column headers 
            $(colheader).hide();

            // Show bulk-delete form
            $(bulkActions).show();

            // If not checked 
        } else {

            // Add/Remove a CSS class to each row 
            $(this).closest('tr').removeClass(selectedRow);

            if (itemCount === 0) {

                // Hide bulk-delete form
                $(bulkActions).hide();

                // Show column headers 
                $(colheader).show();
            }
        }

        // Update drop-down text with new text
        $(updateScope + ' option:first').text(scopeOptionText);
    });

    // Listens for `change` event on `selectAll` checkbox
    $('body').on('change', selectAll, function() {

        // Saves `selectAll` checkbox status 
        var checkedStatus = this.checked;

        // Loop over all checkbox items on the page 
        $(checkedItems).each(function() {

            // Set this checkbox status based on status of the `selectAll` checkbox
            $(this).prop('checked', checkedStatus);

            // Make changes
            $(this).trigger('change');
        });
    });
};


// Handling processing payments with Stripe
// Overrides form's default behavior
var stripe = function() {

    // This payment form ID corresponds to the payment template ID
    var $form = $('#payment_form');

    // This is being populated in a hidden form field from Flask
    var $stripeKey = $('#stripe_key');

    var $paymentErrors = $('.payment-errors');
    var $spinner = $('.spinner');

    // ...
    var errors = {
        'missing_name': 'You must enter your name.'
    };

    // This identifies your website in the `createToken` call below
    // Tells JS to use our stripe key value
    if ($stripeKey.val()) {
        Stripe.setPublishableKey($stripeKey.val());
    }

    // This get executed after stripe received the form (it knows it came from our site)
    var stripeResponseHandler = function(status, response) {

        // Hide payment errors 
        $paymentErrors.hide();

        // If there's an error from Stripe
        if (response.error) {

            // Hide spinner gif
            $spinner.hide();

            // Enable submit button
            $form.find('button').prop('disabled', false);

            // Show error 
            $paymentErrors.text(response.error.message);
            $paymentErrors.show();
        }

        // There's no error from Stripe
        else {

            // Save token we get from Stripe
            // This token contains: id, last 4 digits, and card type
            // Note: This is one-time, that proves the user's credit card details are valid, 
            //       and they want to create a subscription, that's associated to our Stripe account 
            //       On the Flask side, we need to provide this to Stripe to create the subscription
            var token = response.id;

            // Save token in hidden field, append it to the form (so it gets submit to the server)
            var field = '<input type="hidden" id="stripe_token" name="stripe_token" />';
            $form.append($(field).val(token));

            // Show spinner gif
            $spinner.show();

            // Process the payment by submitting the form
            $form.get(0).submit();
        }
    };

    // Formats either percent off or amount off
    var discountType = function(percentOff, amountOff) {
        if (percentOff) {
            return percentOff + '%';
        }
        return '$' + amountOff;
    };

    // ...
    jQuery(function($) {

        // CSRF token to protect forms not from `WTForms`
        var csrfToken = $('meta[name=csrf-token]').attr('content');

        // This gets executed immediately when we submit the form
        $('body').submit(function() {

            // Save variables 
            var $form = $(this);
            var $name = $('#name');

            // Show spinner gif 
            $spinner.show();

            // Hide form errors 
            $paymentErrors.hide();

            // Custom check to make sure their name exists (before calling Stripe)
            if ($name.val().length === 0) {

                // Show missing name error 
                $paymentErrors.text(errors.missing_name);
                $paymentErrors.show();

                // Hide spinner
                $spinner.hide();

                return false;
            }

            // Name is valid - Disable the submit button to prevent repeated clicks
            $form.find('button').prop('disabled', true);

            // Call Stripe - if success, `stripeResponseHandler` gets executed afterwards
            Stripe.card.createToken($form, stripeResponseHandler);

            // Prevent the form from submitting with the default action
            return false;
        });
    });
};

// Initialize everything when the browser is ready
$(document).ready(function() {
    momentjsClasses();
    bulkDelete();
    stripe();
});