"""Implementation of a L2 learning self. The self learns the location of a
source since it knows on which port the incoming frame arrived at. It stores
the MAC address and the port at which the frame arrived at in its 
forwarding table. This is done for ec=very new sender whose MAC address is not in
the forarding table. 
This forwarding table is used by the self to forwad frames appropriately to
the destination. If a particular destination is not in the table, then the 
frame is forwarded to all ports (flooding).
The self drops the frame if the destination MAC address is on the same port as
the one it arrived on"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpid_to_str
from pox.lib.util import str_to_bool
import time

log = core.getLogger()

flood_delay = 0

class LearningSwitch(object):
	def __init__(self,connection,transparent):
		#Setting up the switch
		self.connection = connection
		self.transparent = transparent
		#Forwarding Table
		self.macToPort = {}
		#Listening to ports
		connection.addListeners(self)
		self.hold_down_expired = flood_delay == 0	#TRUE

	def _handle_PacketIn(self,event):
		#Handling incoming frames and updating the forwarding table
		frame = event.parsed
	
		#Flooding mode
		def flood(message = None):
			msg = of.ofp_packet_out()
			if time.time() - self.connection.connect_time >= flood_delay:
				if self.hold_down_expired is False:
					self.hold_down_expired = True
					log.info("%s: Flood hold-down expired -- flooding",
			   		dpid_to_str(event.dpid))

				if message is not None: log.debug(message)
				msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
			else:
				pass
			msg.data = event.ofp
			msg.in_port = event.port
			self.connection.send(msg)

		#Drop mode if destination is on the same port as the incoming port
		def drop(duration = None):
			if duration is not None:
				if not isinstance(duration, tuple):
					duration = (duration,duration)
				msg = of.ofp_flow_mod()
				msg.match = of.ofp_match.from_packet(frame)
				msg.idle_timeout = duration[0]
				msg.hard_timeout = duration[1]
				msg.buffer_id = event.ofp.buffer_id
				self.connection.send(msg)
			elif event.ofp.buffer_id is not None:
				msg = of.ofp_packet_out()
				msg.buffer_id = event.ofp.buffer_id
				msg.in_port = event.port
				self.connection.send(msg)
	
		self.macToPort[frame.src] = event.port
		if not self.transparent:
			if frame.type == frame.LLDP_TYPE or frame.dst.isBridgeFiltered():
				drop()
				return
		if frame.dst.is_multicast:
			flood()
		else:
			if frame.dst not in self.macToPort:
				flood("Port for %s unknown -- flooding" % (frame.dst,))
			else:
				port = self.macToPort[frame.dst]
				if port == event.port:
					log.warning("Same port for frame from %s -> %s on %s.%s.  Drop."
							% (frame.src, frame.dst, dpid_to_str(event.dpid), port))
					drop(10)
					return
				log.debug("installing flow for %s.%i -> %s.%i" %(frame.src, event.port, frame.dst, port))
				msg = of.ofp_flow_mod()
				msg.match = of.ofp_match.from_packet(frame, event.port)
				msg.idle_timeout = 15
				msg.hard_timeout = 30
				msg.actions.append(of.ofp_action_output(port = port))
				msg.data = event.ofp
				self.connection.send(msg)

class learning_switch(object):
	def __init__ (self, transparent):
		core.openflow.addListeners(self)
		self.transparent = transparent

	def _handle_ConnectionUp (self, event):
		log.debug("Connection %s" % (event.connection,))
		LearningSwitch(event.connection, self.transparent)

def launch (transparent=False, hold_down=flood_delay):
	try:
		global flood_delay
		flood_delay = int(str(hold_down), 10)
		assert flood_delay >= 0
	except:
		raise RuntimeError("Expected hold-down to be a number")

	core.registerNew(learning_switch, str_to_bool(transparent))
