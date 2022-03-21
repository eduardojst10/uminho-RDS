from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0
from ryu.lib.mac import haddr_to_bin
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types



class L2Switch(app_manager.RyuApp):
    
    def __init__(self, *args, **kwargs):
        super(L2Switch, self).__init__(*args, **kwargs)
        self.mac_ports = {}


    # decorador que diz ao ryu quando a função deverá ser chamada
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER) # Switch-features message received and sent set-config message, this function is called only after the negotiation completes.
    def packet_in_handler(self, ev):
        msg = ev.msg #object that represents a packet_in data structure. An object que descreve a correspondente OpenFlow message 

        dp = msg.datapath # object that represents a datapath (switch). basicamente é o switch de onde recebemos o packet
        

        # são objectos que representam o protocolo openFlow negociado entre Ryu e o switch
        ofp = dp.ofproto 
        ofp_parser = dp.ofproto_parser


        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        # vamos ignorar link layer discovery protocol packets
        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        dest = eth.dst
        source = eth.src

        #id de switch
        dpid = dp.id

        self.mac_ports.setdefault(dpid,{})

        self.logger.info("packet in %s %s %s %s", dpid, source, dest, msg.in_port)

        self.mac_ports[dpid][source] = msg.in_port

        if dest in self.mac_ports[dpid]:
            out_port = self.mac_ports[dpid]
        
        else:
            out_port = ofp.OFPP_FLOOD

        # o que o switch vai fazer é enviar a mensagem para o out_port
        #OFPActionOutput class é useda com uma mensagem packet_out para especificar uma porta de switch da qual você deseja enviar o pacote. 
        
        actions = [ofp_parser.OFPActionOutput(out_port)]

        #vamos adicionar novo flow à nossa tabela de entradas de flows
        #adicionamos novo flow com timeout e cenas especificas

        if out_port != ofp.OFPP_FLOOD:
            self.adiciona_flow(dp,msg.in_port,dest,source,actions)
            
            

        data = None
        if msg.buffer_id == ofp.OFP_NO_BUFFER:
             data = msg.data


        #classe OFPPacketOut class é usada para construir um packet_out message
        out = ofp_parser.OFPPacketOut(
            datapath=dp, buffer_id=msg.buffer_id, in_port=msg.in_port,
            actions=actions, data = data)
        dp.send_msg(out)


    #Pq é constituido um flow mod de OF?
    def adiciona_flow(self,dpath,in_port,dst,src,actions):
        ofp = dpath.ofproto

        #o match que é dado mal chegue um pacote
        match = dpath.ofproto_parser.OFPMatch(
            in_port = in_port,
            dls_dst = haddr_to_bin(dst), 
            dl_src=haddr_to_bin(src)
        )

        mod = dpath.ofproto_parser.OFPFlowMod(
            datapath = dpath,
            match = match,
            cookie = 0,
            command= ofp.OFPFC_ADD,
            idle_timeout=0,
            hard_timeout=0,
            priority=ofp.OFP_DEFAULT_PRIORITY,
            flags=ofp.OFPFF_SEND_FLOW_REM, 
            actions=actions
        )
        # é enviada uma flow modification message
        # criamos assim flow entry na tabela do switch
        dpath.send_msg(mod)


        
        
        

        