from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0




class L2Switch(app_manager.RyuApp):
    
    def __init__(self, *args, **kwargs):
        super(L2Switch, self).__init__(*args, **kwargs)
        self.mac_ports = {}



    # decorador que diz ao ryu o ha
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER) # Switch-features message received and sent set-config message
    def packet_in_handler(self, ev):
        msg = ev.msg #object that represents a packet_in data structure. An object que descreve a correspondente OpenFlow message 

        dp = msg.datapath # object that represents a datapath (switch). basicamente é o switch de onde recebemos o packet
        

        # são objectos que representam o protocolo openFlow negociado entre Ryu e o switch
        ofp = dp.ofproto 
        ofp_parser = dp.ofproto_parser


        #OFPActionOutput class é useda com uma mensagem packet_out para especificar uma porta de switch da qual você deseja enviar o pacote. 
        # Este aplicativo usa o sinalizador OFPP_FLOOD para indicar que o pacote deve ser enviado em todas as portas.

        actions = [ofp_parser.OFPActionOutput(ofp.OFPP_FLOOD)]

        data = None
        if msg.buffer_id == ofp.OFP_NO_BUFFER:
             data = msg.data

        #classe OFPPacketOut class é usada para construir um packet_out message
        out = ofp_parser.OFPPacketOut(
            datapath=dp, buffer_id=msg.buffer_id, in_port=msg.in_port,
            actions=actions, data = data)
        dp.send_msg(out)

        