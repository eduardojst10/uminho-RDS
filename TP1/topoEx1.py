from mininet.topo import Topo 


class MyTopo( Topo ):
    "TP1 topoEx1 example."

    def build( self ):
        "Create custom topoEx1."

        # Add hosts and switches
        switch = self.addSwitch("s1")
        h1 = self.addHost( 'h1' )
        h2 = self.addHost( 'h2' )
        h3 = self.addHost( 'h3' )
        h4 = self.addHost( 'h4' )
        # Add links
        self.addLink( h1, switch )
        self.addLink( h2, switch )
        self.addLink( h3, switch )
        self.addLink( h4, switch )


topos = { 'mytopo': ( lambda: MyTopo() ) }