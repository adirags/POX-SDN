# Learning Switch
Implementation of a L2 switch using the POX controller.
To run the switch, first ensure you have pox installed on your system. The controller can be run by typing
  ./pox.py learning_switch

To test the controller, mininet can be used. Create a topology and ping hosts to view how the controller eithr floods or 
forwards the frame to ensure that the host receives the ICMP (ping) request and reply.
To create your own topology, you can use the following command (you need mininet to run this)
   sudo mn --topo single,5 --mac --switch ovsk --controller remote
