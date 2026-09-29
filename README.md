cp ~/.termux/termux.properties ~/.termux/termux.properties.bak
   sed -i '/^[[:space:]]*extra-keys[[:space:]]*=/d' ~/.termux/termux.properties
   printf '\nextra-keys = [[ESC,TAB,CTRL,ALT,DOWN,UP,{macro:"CTRL a c",display:"NEW"}]]\n' >> ~/.termux/termux.properties
   termux-reload-settings
