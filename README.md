mkdir -p ~/.termux
   printf '%s\n' 'extra-keys = [["ESC","TAB","CTRL","ALT","DOWN","UP"],[{"macro":"CTRL a c","display":"NEW"},{"macro":"CTRL a
 n","display":"NEXT"},{"macro":"CTRL a p","display":"PREV"},{"macro":"CTRL a d","display":"OUT"}]]' >> ~/.termux/termux.properties
   termux-reload-settings
