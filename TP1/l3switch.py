from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ether_types, ethernet, arp, icmp, ipv4


class L3switch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(L3switch, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        # aqui definimos as interfaces que possuimos no router/l3switch e seus dados = routing_table
        #                    port/ interface / ip/network ip
        self.interfaces[3] = [[1, "10.0.0.1", "10.0.0.0/24"],
                              [2,"10.0.1.1","10.0.1.0/24"],
                              [3,"10.0.2.1","10.0.2.0/24"]]

        # Definimos os macs dessas Interfaces
        # Foram gerados aleatoriamente
        self.ip_mac = {"10.0.0.1":"B9:B5:3D:9A:E3:66",
                        "10.0.1.1":"E2:FA:8A:1F:99:10",
                        "10.0.2.1":"75:5D:00:B4:73:34"}

    # the switch_features_handler will 
    # listen on this event and add a send all flow to controller flow on the switch.(table-miss flow)
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        
        # é enviada uma flow modification message
        # criamos assim flow entry na tabela do switch
        datapath.send_msg(mod)


    # decorador que diz ao ryu quando a função deverá ser chamada
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        
        msg = ev.msg # Objecto que descreve a correspondente OpenFLow message = Packet_in
        datapath = msg.datapath # Objecto que representa o datapath (switch), é o switch de onde recebemos os packet_in
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']


        #------------ Pkt recebido , de onde tiramos toda a nossa informação        
        pkt = packet.Packet(msg.data)
        pkt_eth = pkt.get_protocols(ethernet.ethernet)[0]

        
        # vamos ignorar link layer discovery protocol packets
        if pkt_eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        


        #------------ ARP 
        pkt_arp = pkt.get_protocol(arp.arp)
        # Dado um Match com um ARP Request
        # Verifico que ip corresponde ao ip de request e 
        # envio um ARP Reply com o meu MAC associado à interface correta
        if pkt_arp:
            # se o ip for meu?
            self.handle_arp(datapath,in_port,pkt_eth,pkt_arp)
            return
 
            
        #------------ ICMP

        pkt_icmp = pkt.get_protocol(icmp.ipv4)
        if pkt_icmp:
            pkt_ipv4 = pkt.get_protocol(ipv4.ipv4)
            self.handle_icmp(datapath,in_port,pkt_eth,pkt_ipv4,pkt_icmp)
            return


        #------------ Controlo de dictionary de MAC src e port associada


        # MACs dst e src
        dst = pkt_eth.dst
        src = pkt_eth.src
        #id de switch
        dpid = format(datapath.id, "d").zfill(16)
        self.mac_to_port.setdefault(dpid, {})

        # manutencao de logs
        self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)


        # Popular o dictionary com MACs
        # Dictionary com o input packet’s source MAC Address and input port.
        self.mac_to_port[dpid][src] = in_port

   
        # Then use that same dictionary and with the destination MAC address find out the packet’s destination
        # Usar o mesmo dicionario com o MAC addr dst para descobrir a porta de destino
        # Se é nula entao nao necessitamos de criar um of_flow_mod

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD


        # O que o switch vai fazer é enviar a mensagem para o out_port
        # OFPActionOutput class é usada com uma mensagem packet_out para especificar uma porta de switch para qual se envia o pacote. 
        actions = [parser.OFPActionOutput(out_port)]

      
        # Adicionamos novo flow com timeout e cenas especificas a uma de tabelas de flows?


        
        # Submeter um novo flow de modo a evita packet_in na proxima vez
        # Caso a porta de saida não seja nula, temosd de criar um novo of_flow_modobject com um match field
        # (dst MAC address) and a action field (sent to ’destination port’)
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=src)
            
            # Verificacao de buffer_id válido, if yes avoid to send both 
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        # classe OFPPacketOut é usada para construir um packet_out
        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)


    # necessito de adicionar novos flows??
    def handle_arp(self,datapath,port,pkt_ethernet,pkt_arp):

        if pkt_arp.opcode != arp.ARP_REQUEST:
            return
        

        #Match do ip do qual queremos o mac
        ip_wanted = pkt_arp.dst_ip

        #vou buscar o mac pretendido
        mac_wanted = self.ip_mac[ip_wanted]

        #crio um novo packet de arp reply
        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=pkt_ethernet.ethertype,
                                           dst=pkt_ethernet.src,
                                           src=mac_wanted))


        pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                 src_mac=mac_wanted,
                                 src_ip=ip_wanted,
                                 dst_mac=pkt_arp.src_mac,
                                 dst_ip=pkt_arp.src_ip))

        # crio o packet_out
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        pkt.serialize()
        self.logger.info("packet-out without arp request %s" % (pkt,))
        data = pkt.data
        actions = [parser.OFPActionOutput(port=port)]
        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=ofproto.OFP_NO_BUFFER,
                                  in_port=ofproto.OFPP_CONTROLLER,
                                  actions=actions,
                                  data=data)
        datapath.send_msg(out)

    # necessito de adicionar novos flows??
    def handle_icmp(self, datapath, port, pkt_ethernet, pkt_ipv4, pkt_icmp):
        if pkt_icmp.type != icmp.ICMP_ECHO_REQUEST:
            return

        #Match do ip do qual queremos o mac
        ip_wanted = pkt_icmp.dst_ip

        #vou buscar o mac pretendido
        mac_wanted = self.ip_mac[ip_wanted]

        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(ethertype=pkt_ethernet.ethertype,
                                           dst=pkt_ethernet.src,
                                           src=mac_wanted))
        pkt.add_protocol(ipv4.ipv4(dst=pkt_ipv4.src,
                                   src=self.ip_addr,
                                   proto=pkt_ipv4.proto))

        pkt.add_protocol(icmp.icmp(type_=icmp.ICMP_ECHO_REPLY,
                                   code=icmp.ICMP_ECHO_REPLY_CODE,
                                   csum=0,
                                   data=pkt_icmp.data))

        # crio o packet_out
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        pkt.serialize()
        self.logger.info("packet-out without icmp echo ping %s" % (pkt,))
        data = pkt.data
        actions = [parser.OFPActionOutput(port=port)]
        out = parser.OFPPacketOut(datapath=datapath,
                                  buffer_id=ofproto.OFP_NO_BUFFER,
                                  in_port=ofproto.OFPP_CONTROLLER,
                                  actions=actions,
                                  data=data)
        datapath.send_msg(out)
        
        
