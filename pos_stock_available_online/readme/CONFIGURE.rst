In "Point of Sale" configuration "Product Quantity" section activate "Display Product Quantity" feature:
  .. image:: ../static/img/pos_config.png

By default quantity is displayed for the warehouse that is used in the POS stock operation type.

You can add additional warehouses to show quantity in by adding them into "Additional Warehouses" field.

In this case the following information will be displayed on product tiles:

- Total quantity = quantity in the default warehouse + quantity in the additional warehouses

- Quantity in the default warehouse

- Quantity in the additional warehouses.

It's important to consider when configuring the channels, to add the 'root.pos_stock_notification' 
channel to server configuration.

It is not recommended for the thread limit reserved for this channel to exceed 25% of the total.