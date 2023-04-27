La configuración necesaria para canjear vales/TR's cómo métodos de pago es:

En un programa de tipo **tarjeta regalo**, seleccionar el campo `Método de canje` cómo **"Método de pago".**

.. image:: pos_loyalty_redeem_payment/static/img/redeemMethod.png
   :width: 300
   :alt: config

Se deberá configurar un **"método de pago"** en el programa. El cual se asocia a los métodos de pago del TPV.

.. image:: pos_loyalty_redeem_payment/static/img/paymentMethod.png
   :width: 300
   :alt: config


En los métodos de pago, el campo `Código para canje` no es editable, se activa si:
 - Tenemos un método de pago asociado a un **programa.**
 - El campo `Método de canje` está configurado como **"Método de pago".**
