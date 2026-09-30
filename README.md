cp ~/.termux/termux.properties ~/.termux/termux.properties.pre-new
   printf '\nextra-keys = [["ESC","TAB","CTRL","ALT",{"key":"F2","display":"NEW"},"DOWN","UP"]]\n' >> ~/.termux/termux.properties
   termux-reload-settings
