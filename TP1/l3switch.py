from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3, ether
from ryu.lib.packet import packet, ether_types, ethernet, arp, icmp, ipv4


class L3switch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(L3switch, self).__init__(*args, **kwargs)
        



        """
            Tabela de routing para L3Switch

            MAC para cada interface do L3Switch

            ARP Cache para saber MAC addr de diferentes hosts
        """

        # aqui definimos as interfaces que possuimos no router/l3switch e seus dados = routing_table
        #                              ip_host    interface ip/network ip / port 
        self.interfaces_routing = { "10.0.0.2/24":["10.0.0.1", "10.0.0.0/24",1],
                                    "10.0.0.3/24":["10.0.0.1", "10.0.0.0/24",1],
                                    "10.0.0.4/24":["10.0.0.1", "10.0.0.0/24",1],
                                    "10.0.1.2/24":["10.0.1.1", "10.0.1.0/24",2],
                                    "10.0.1.3/24":["10.0.1.1", "10.0.1.0/24",2],
                                    "10.0.1.4/24":["10.0.1.1", "10.0.1.0/24",2],
                                    "10.0.2.2/24":["10.0.2.1", "10.0.2.0/24",3],
                                    "10.0.2.3/24":["10.0.2.1", "10.0.2.0/24",3],
                                    "10.0.2.4/24":["10.0.2.1", "10.0.2.0/24",3],
                                }

        # Definimos os macs dessas Interfaces
        # Foram gerados aleatoriamente
        # Tem de ser iguais aos do mininet
        self.ip_mac = {"10.0.0.1":"B9:B5:3D:9A:E3:66",
                        "10.0.1.1":"E2:FA:8A:1F:99:10",
                        "10.0.2.1":"75:5D:00:B4:73:34"}


        # Cache de ARP
        self.cache_arp={}

        # MAC e ports associados
        self.mac_to_port = {}

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
        pkt_icmp =  pkt.get_protocol(icmp.icmp)
        pkt_ipv4 = pkt.get_protocol(ipv4.ipv4)

        if pkt_icmp:           
            self.handle_icmp(datapath,in_port,pkt_eth,pkt_ipv4,pkt_icmp)
            return

            
        #------------ ONLY IPv4
        if pkt_ipv4:
            self.handle_ipv4(datapath,in_port,pkt_eth,pkt_ipv4)
            return 
        


    # Ver com o stor
    def handle_arp(self,datapath,port,pkt_ethernet,pkt_arp):      
        # Apenas guardo em cache se for ARP Reply
        if pkt_arp.opcode == arp.ARP_REPLY:
            # Vejo para quem é
            # Guardo a cache do src ip o seu MAC
            ip_to_cache = pkt_arp.src_ip
            mac_to_cache = pkt_arp.dst_mac

            self.cache_arp[ip_to_cache] = mac_to_cache

            return
        
        else:
            
            #Match do ip do qual queremos o mac
            ip_wanted = pkt_arp.dst_ip
            
            # Verificar se é para mim 
            # Se o endereço não for um das minhas interfaces então não mando nenhum packet_out
            if ip_wanted not in self.ip_mac.keys():
                return
            else:
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
            
    # Provavelmente Incompleto
    def handle_ipv4(self, datapath, port, pkt_ethernet, pkt_ipv4):
        # Vamos usar a cache_arp para verificar se temos o endereço mac do destino, se não tivermos 
        # termos de enviar um arp request

        # Com IP de host tenho dados sobre por onde vou dar forwarding do meu router/L3switch 
        data_ipdst = self.interfaces_routing[pkt_ipv4.src]

        # IP de interface do router/L3Switch
        src_ip_interface = data_ipdst[0]

        # MAC de interface do router/L3Switch
        src_mac_interface = self.ip_mac[src_ip_interface]

        #Verifico se tenho MAC de host dst
        mac_dst = self.cache_arp[pkt_ipv4.dst]

        s = 0
        if mac_dst:
            pkt = packet.Packet()
            pkt.add_protocol(ethernet.ethernet(ethertype=pkt_ethernet.ethertype,
                                            dst=mac_dst,
                                            src=src_mac_interface))
            pkt.add_protocol(ipv4.ipv4(dst=pkt_ipv4.dst,
                                    src=src_ip_interface,
                                    proto=pkt_ipv4.proto))

        else:
            s =1
            # Se não possuir MAC na cache envio ARP Request
            pkt = packet.Packet()
            pkt.add_protocol(ethernet.ethernet(
                                ethertype=ether.ETH_TYPE_ARP,
                                src=src_mac_interface))

            pkt.add_protocol(arp.arp(opcode=arp.ARP_REQUEST,
                                src_mac=src_mac_interface,
                                src_ip=src_ip_interface,
                                dst_ip=pkt_ipv4.dst))



        # crio o packet_out
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        pkt.serialize()
        if s == 0:
            self.logger.info("packet-out with forwarding IPv4 packet %s" % (pkt,))
        else:
            self.logger.info("packet-out with ARP Request %s" % (pkt,))

        data = pkt.data
        actions = [parser.OFPActionOutput(port=port)]
        out = parser.OFPPacketOut(datapath=datapath,
                                buffer_id=ofproto.OFP_NO_BUFFER,
                                in_port=ofproto.OFPP_CONTROLLER,
                                actions=actions,
                                data=data)
        datapath.send_msg(out)              
        return
        

    # Incompleto provavelmente
    def handle_icmp(self, datapath, port, pkt_ethernet, pkt_ipv4, pkt_icmp):
        if pkt_icmp.type != icmp.ICMP_ECHO_REQUEST:
            return

        else:

            # Com IP de host tenho dados sobre por onde vou dar forwarding do meu router/L3switch 
            data_ipdst = self.interfaces_routing[pkt_ipv4.src]

            # IP de interface do router/L3Switch
            src_ip_interface = data_ipdst[0]

            # MAC de interface do router/L3Switch
            src_mac_interface = self.ip_mac[src_ip_interface]



            pkt = packet.Packet()
            pkt.add_protocol(ethernet.ethernet(ethertype=pkt_ethernet.ethertype,
                                            dst=pkt_ethernet.src,
                                            src=src_mac_interface))
            pkt.add_protocol(ipv4.ipv4(dst=pkt_ipv4.src,
                                    src=src_ip_interface,
                                    proto=pkt_ipv4.proto))

            pkt.add_protocol(icmp.icmp(type_=icmp.ICMP_ECHO_REPLY,
                                    code=icmp.ICMP_ECHO_REPLY_CODE,
                                    csum=0,
                                    data=pkt_icmp.data))

            # crio o packet_out
            ofproto = datapath.ofproto
            parser = datapath.ofproto_parser
            pkt.serialize()
            self.logger.info("packet-out with icmp echo ping %s" % (pkt,))
            data = pkt.data
            actions = [parser.OFPActionOutput(port=port)]
            out = parser.OFPPacketOut(datapath=datapath,
                                    buffer_id=ofproto.OFP_NO_BUFFER,
                                    in_port=ofproto.OFPP_CONTROLLER,
                                    actions=actions,
                                    data=data)
            datapath.send_msg(out)
