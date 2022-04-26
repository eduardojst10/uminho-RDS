from asyncio import protocols
from mininet.topo import Topo 
from mininet.node import Controller, RemoteController, OVSKernelSwitch, UserSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import Link, TCLink

class MyTopo( Topo ):
    "TP2 topoEx2 example."

    def build( self ):
        "Create custom topoEx2."

        # Add hosts and switches
        switch1 = self.addSwitch("s1",dpid = "0000000001",protocol = "OpenFlow13")
        h11 = self.addHost( 'h11', ip = "10.0.0.2/24", defaultroute = "via 10.0.0.1" )
        h21 = self.addHost( 'h21', ip = "10.0.0.3/24", defaultroute = "via 10.0.0.1" )
        h31 = self.addHost( 'h31', ip = "10.0.0.4/24", defaultroute = "via 10.0.0.1" )
        # Add links
        self.addLink( h11, switch1 )
        self.addLink( h21, switch1 )
        self.addLink( h31, switch1 )

        # Add hosts and switches
        switch2 = self.addSwitch("s2",dpid = "0000000002",protocol = "OpenFlow13")
        h12 = self.addHost( 'h12', ip = "10.0.1.2/24", defaultroute = "via 10.0.1.1" )
        h22 = self.addHost( 'h22', ip = "10.0.1.3/24", defaultroute = "via 10.0.1.1" )
        h32 = self.addHost( 'h32', ip = "10.0.1.4/24", defaultroute = "via 10.0.1.1" )
        # Add links
        self.addLink( h12, switch2 )
        self.addLink( h22, switch2 )
        self.addLink( h32, switch2, delay = '5ms')

        # Add hosts and switches
        switch3 = self.addSwitch("s3",dpid = "0000000003",protocol = "OpenFlow13")
        h13 = self.addHost( 'h13', ip = "10.0.2.2/24", defaultroute = "via 10.0.2.1" )
        h23 = self.addHost( 'h23', ip = "10.0.2.3/24", defaultroute = "via 10.0.2.1" )
        h33 = self.addHost( 'h33', ip = "10.0.2.4/24", defaultroute = "via 10.0.2.1" )
        # Add links
        self.addLink( h13, switch3 )
        self.addLink( h23, switch3 )
        self.addLink( h33, switch3, loss = 10)

        
        switchL3 = self.addSwitch("swl3",dpid = "0000000004",protocol = "OpenFlow13")
        self.addLink( switch1, switchL3, delay = '5ms')
        self.addLink( switch2, switchL3 )
        self.addLink( switch3, switchL3 )

        


topos = { 'mytopo': ( lambda: MyTopo() ) }