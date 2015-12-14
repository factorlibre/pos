/* © 2015 FactorLibre - Ismael Calvo <ismael.calvo@factorlibre.com>
 * License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
 */

openerp.pos_return_voucher = function(instance, local) {
    module = instance.point_of_sale;
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;


    module.ActionBarWidget = module.ActionBarWidget.extend({
        set_button_hidden: function(name, hidden){
            var b = this.buttons[name];
            if(b){
                b.set_hidden(hidden);
            }
        },
    });


    module.ActionButtonWidget = module.ActionButtonWidget.extend({
        set_hidden: function(hide){
            if(this.hide != hide){
                this.hide = !!hide;
                this.renderElement();
            }
        },
        renderElement: function(){
            this._super();
            if(this.hide){
                this.$el.addClass('hidden');
            } else {
                this.$el.removeClass('hidden');
            }
        },
    });


    var OrderSuper = module.Order;
    module.Order = module.Order.extend({
        initialize: function(attributes){
            OrderSuper.prototype.initialize.call(this, attributes);
            this.used_voucher = attributes.used_voucher || false;
        },
        get_used_voucher: function(){
            return this.used_voucher;
        },
        set_used_voucher: function(voucher){
            this.used_voucher = voucher;
        },
        get_picked_vouchers: function(){
            picked_voucher_ids= []
            paymentLines = this.attributes.paymentLines
            for (var i=0, len=paymentLines.length; i<len; i++) {
                payment_line = paymentLines.models[i];
                if (payment_line.voucher) {
                    picked_voucher_ids.push(payment_line.voucher.id)
                }
            };
            return picked_voucher_ids
        },
    });


    var PaymentlineSuper = module.Paymentline;
    module.Paymentline = module.Paymentline.extend({
        initialize: function(attributes, options) {
            res = PaymentlineSuper.prototype.initialize.call(this, attributes, options);

            // How to protect this?
            this.voucher = false
        },


        set_amount: function(value){
            // TODO the param value comes wrong when is a float
            var self = this;

            if(self.voucher) {
                var currentOrder = this.pos.get('selectedOrder');
                total = currentOrder.getTotalTaxIncluded();
                if (total < 0) {
                    value = total;
                } else if (value > self.voucher.amount){
                    value = self.voucher.amount;
                }
                this.node.querySelector('input').value = value;
            }

            PaymentlineSuper.prototype.set_amount.call(this, value);
        },

        set_voucher: function(payment_line, voucher){
            if(this.voucher !== voucher){
                this.voucher = voucher;
                payment_line.set_amount(voucher.amount);
            }
            this.trigger('change:voucher', this);
        },
        get_voucher: function(){
            return this.voucher;
        }
    });


    module.PaypadButtonWidget = module.PaypadButtonWidget.extend({
        renderElement: function() {
            this._super();
            var self = this;

            this.$el.click(_.bind(function(){
                var currentOrder = this.pos.get('selectedOrder');
                paymentLines = currentOrder.get('paymentLines');
                line_for_voucher = false
                for (var i=0, len=paymentLines.length; i<len; i++) {
                    payment_line = paymentLines.models[i];
                    if (!payment_line.voucher && payment_line.cashregister.journal.voucher_journal && payment_line.cashregister.id === self.cashregister.id) {
                        line_for_voucher = payment_line;
                        break;
                    }
                };
                if (line_for_voucher) {
                    self.pos.pos_widget.screen_selector.show_popup('voucherpopup', {
                        'message': _t('Choose a voucher'),
                        'order_id': self.current_order_id,
                        'payment_line': line_for_voucher
                    });
                };
            }, self));
        }
    });


    module.PaymentScreenWidget = module.PaymentScreenWidget.extend({
        show: function(){
            this._super();
            var self = this;

            voucher_btn = this.add_action_button({
                label: _t('Return Voucher'),
                name: 'return_voucher',
                icon: '/point_of_sale/static/src/img/scan.png',
                click: function(){
                    self.validate_return_order();
                },
            });

            voucher_btn.$('img').css('height', '40px');

            // Hide 'Validate' & 'Invoice' buttons if return order
            var currentOrder = this.pos.get('selectedOrder');
            if (currentOrder.getTotalTaxIncluded() < 0) {
                this.pos_widget.action_bar.set_button_hidden('validation', true);
                this.pos_widget.action_bar.set_button_hidden('invoice', true);
                this.pos_widget.payment_screen.next_screen = 'voucher_receipt';
            } else {
                this.pos_widget.action_bar.set_button_hidden('return_voucher', true);
                this.pos_widget.payment_screen.next_screen = 'receipt';
            }
        },

        create_voucher: function() {
            var self = this;
            var currentOrder = this.pos.get('selectedOrder');
            total = currentOrder.getTotalTaxIncluded();
            config = this.pos.config;
            due_date = false
            if (config.vouchers_expire) {
                due_date = new Date();
                due_date.setDate(due_date.getDate() + config.voucher_validity_period);
            }
            vals = {
                'amount': total * -1,
                'due_date': due_date,
            }
            posVoucherModel = new instance.web.Model('pos.voucher')
            return posVoucherModel.call('create_from_ui', [vals])
            .then(function (result) {
                return result;
            }).fail(function (error, event){
                if (parseInt(error.code) === 200) {
                    // Business Logic Error, not a connection problem
                    self.pos.pos_widget.screen_selector.show_popup(
                        'error-traceback', {
                            message: error.data.message,
                            comment: error.data.debug
                        }
                    );
                }
                else{
                    self.pos_widget.screen_selector.show_popup('error',{
                        message: _t('Connection error'),
                        comment: _t('Can not execute this action because the POS is currently offline'),
                    });
                }
            });
        },

        validate_order: function(){
            // TODO check voucher in py before validate order?
            // the voucher is checked from js
            var self = this;
            this._super();
            var currentOrder = this.pos.get('selectedOrder');
            paymentLines = currentOrder.get('paymentLines')
            for (var i=0, len=paymentLines.length; i<len; i++) {
                payment_line = paymentLines.models[i];
                if(payment_line.voucher){
                    var voucherModel = new instance.web.Model('pos.voucher');
                    data = [
                        payment_line.voucher.id,
                        payment_line.amount
                    ]
                    config = this.pos.config;
                    if (payment_line.amount < 0 && config.vouchers_expire) {
                        due_date = new Date();
                        due_date.setDate(due_date.getDate() + config.voucher_validity_period);
                        if (due_date > payment_line.voucher.due_date) {
                            data.push(due_date);
                        }
                    }
                    return voucherModel.call('use_voucher', data)
                    .fail(function (error, event){
                        if (parseInt(error.code) === 200) {
                            // Business Logic Error, not a connection problem
                            self.pos_widget.screen_selector.show_popup(
                                'error-traceback', {
                                    message: error.data.message,
                                    comment: error.data.debug
                                }
                            );
                        }
                        else{
                            self.pos_widget.screen_selector.show_popup('error',{
                                message: _t('Connection error'),
                                comment: _t('Can not execute this action because the POS is currently offline'),
                            });
                        }
                    });
                }
            };
        },

        // TODO: Refactor
        validate_return_order: function(){
            var self = this;
            var currentOrder = this.pos.get('selectedOrder');
            var create_new_voucher = false;
            var voucher = false;
            paymentLines = currentOrder.get('paymentLines');
            if (paymentLines.length > 1) {
                self.pos_widget.screen_selector.show_popup('error', {
                    message: _t('Voucher Error'),
                    comment: _t('There can only be one payment line in returns. Please, select one and delete the others.'),
                });
            } else if (paymentLines.length == 1) {
                payment_line = paymentLines.models[0];
                if (payment_line.voucher) {
                    voucher = payment_line.voucher;
                } else {
                    create_new_voucher = true;
                }
            } else {
                create_new_voucher = true;
            }

            // TODO: Refactor, NOT DRY
            if (create_new_voucher) {
                voucher = this.create_voucher().done(function (voucher) {
                    currentOrder.set_used_voucher(voucher);
                    self.pos.pos_widget.screen_selector.set_current_screen('voucher_receipt');
                    self.validate_order();
                });

            } else {
                currentOrder.set_used_voucher(voucher);
                self.pos.pos_widget.screen_selector.set_current_screen('voucher_receipt');
                self.validate_order();
            }

        },
    });


    module.PosWidget = module.PosWidget.extend({
        build_widgets: function() {
            this._super();

            this.voucher_receipt_screen = new module.VoucherReceiptScreenWidget(this, {});
            this.voucher_receipt_screen.appendTo(this.$('.screens'));
            this.voucher_receipt_screen.hide();
            this.screen_selector.screen_set['voucher_receipt'] =
                this.voucher_receipt_screen;

            // Init voucher popup
            this.voucher_popup = new module.VoucherPopupWidget(this, {});
            this.voucher_popup.appendTo(this.$el);
            this.voucher_popup.hide();
            this.screen_selector.popup_set['voucherpopup'] =
                this.voucher_popup;
        },
    });


    module.VoucherPopupWidget = module.ConfirmPopupWidget.extend({
        template: 'VoucherPopupWidget',
        model: 'pos.voucher',

        show: function(options) {
            var self = this;
            this.payment_line = options.payment_line;
            options = options || {};
            options.search = this.search_vouchers;
            options.cancel = this.cancel_select_voucher;
            this._super(options);

            this.search_vouchers();

            this.$el.find('.searchbox input').on('keyup',function(){
                self.search_vouchers(this.value);
            });
        },

        cancel_select_voucher: function() {
            this.pos.get('selectedOrder').removePaymentline(this.payment_line);
        },

        render_voucher_list: function(vouchers) {
            var self = this;
            var current_order = this.pos.get('selectedOrder');

            picked_voucher_ids = current_order.get_picked_vouchers()
            contents = this.$('.voucher-list-contents')
            contents[0].innerHTML = '';

            for (var i = vouchers.length - 1; i >= 0; i--) {
                voucher = vouchers[i];
                var voucher_html = $(QWeb.render('LoadVoucherLine',
                    {widget: this, voucher}));

                if (voucher.due_date) {
                    yesterday = new Date();
                    yesterday.setDate(yesterday.getDate() - 1);
                    arr_date = voucher.due_date.split('-')
                    var voucher_due_date = new Date(arr_date[0], arr_date[1], arr_date[2])
                }
                if (picked_voucher_ids.indexOf(voucher.id) == -1 &&
                        voucher.amount > 0 &&
                        (!voucher.due_date || voucher_due_date > yesterday)) {
                    voucher_html.click(_.bind(function(){

                        // Set the voucher
                        self.payment_line.set_voucher(self.payment_line, this);
                        self.pos_widget.screen_selector.close_popup();
                    }, voucher));
                } else {
                    voucher_html.addClass('disabled')
                }
                contents.append(voucher_html)
            };
        },

        search_vouchers: function(query) {
            var self = this;
            var order = self.pos.get_order();
            var curr_client = self.pos.get_order().get_client() || false;
            var voucherModel = new instance.web.Model(this.model);
            return voucherModel.call('search_vouchers', [query || '', curr_client])
            .then(function (result) {
                self.render_voucher_list(result, self.payment_line)
            }).fail(function (error, event){
                if (parseInt(error.code) === 200) {
                    // Business Logic Error, not a connection problem
                    self.pos_widget.screen_selector.show_popup(
                        'error-traceback', {
                            message: error.data.message,
                            comment: error.data.debug
                        }
                    );
                }
                else{
                    self.pos_widget.screen_selector.show_popup('error',{
                        message: _t('Connection error'),
                        comment: _t('Can not execute this action because the POS is currently offline'),
                    });
                }
            });
        },

    });


    module.VoucherReceiptScreenWidget = module.ReceiptScreenWidget.extend({
        refresh: function() {
            var order = this.pos.get('selectedOrder');
            voucher = order.get_used_voucher();
            if (voucher) {
                $('.pos-receipt-container', this.$el).html(QWeb.render('VoucherTicket',{
                    widget:this,
                    voucher: voucher,
                    barcode_src: "/report/barcode?type=Code128&value=" +
                                + voucher.name + "&width=400&height=100",
                    order: order,
                    orderlines: order.get('orderLines').models,
                    paymentlines: order.get('paymentLines'),
                }));
            }
        },
    });

}