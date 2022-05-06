from mininet.net import Mininet

from mininet.node import Controller, RemoteController, OVSSwitch, UserSwitch

from mininet.cli import CLI

from mininet.log import setLogLevel

from mininet.link import Link, TCLink

print ("Starting Mininet")
net = Mininet(controller = RemoteController, switch = OVSSwitch, autoSetMacs = False)

print ("Adding controllers")
c1 = net.addController('c1',controller=RemoteController,ip = '127.0.0.1',port=6633)
c2 = net.addController('c2',controller=RemoteController,ip = '127.0.0.1', port=6634)

s1 = net.addSwitch('s1',cls = OVSSwitch,dpid="0000000000000001")
s2 = net.addSwitch('s2',cls = OVSSwitch,dpid="0000000000000002")
s3 = net.addSwitch('s3',cls = OVSSwitch,dpid="0000000000000003")

print("Created l3switch")
l3switch = net.addSwitch('l3switch',cls=OVSSwitch,dpid="0000000000000004")

h1 = net.addHost('h11', ip = '10.0.0.2/24', mac="00:00:00:00:00:02", defaultRoute = 'via 10.0.0.1')
h2 = net.addHost('h12', ip = '10.0.0.3/24', mac="00:00:00:00:00:03", defaultRoute = 'via 10.0.0.1')
h3 = net.addHost('h13', ip = '10.0.0.4/24', mac="00:00:00:00:00:04", defaultRoute = 'via 10.0.0.1')
h4 = net.addHost('h21', ip = '10.0.1.2/24', mac="00:00:00:00:01:02", defaultRoute = 'via 10.0.1.1')
h5 = net.addHost('h22', ip = '10.0.1.3/24', mac="00:00:00:00:01:03", defaultRoute = 'via 10.0.1.1')
h6 = net.addHost('h23', ip = '10.0.1.4/24', mac="00:00:00:00:01:04", defaultRoute = 'via 10.0.1.1')
h7 = net.addHost('h31', ip = '10.0.2.2/24', mac="00:00:00:00:02:02", defaultRoute = 'via 10.0.2.1')
h8 = net.addHost('h32', ip = '10.0.2.3/24', mac="00:00:00:00:02:03", defaultRoute = 'via 10.0.2.1')
h9 = net.addHost('h33', ip = '10.0.2.4/24', mac="00:00:00:00:02:04", defaultRoute = 'via 10.0.2.1')

net.addLink(s1,l3switch)
net.addLink(s2,l3switch)
net.addLink(s3,l3switch)

net.addLink(h1,s1)
net.addLink(h2,s1)
net.addLink(h3,s1)

net.addLink(h4,s2)
net.addLink(h5,s2)
net.addLink(h6,s2)


net.addLink(h7,s3)
net.addLink(h8,s3)
net.addLink(h9,s3)

l3switch.setMAC('F6:C5:73:99:F4:F7','l3switch-eth1')
l3switch.setMAC('E2:FA:8A:1F:99:10','l3switch-eth2')
l3switch.setMAC('C6:43:79:7E:EA:6B','l3switch-eth3')

net.build()

c1.start()
c2.start()

s1.start([c1])
s2.start([c1])
s3.start([c1])
l3switch.start([c2])

CLI(net)

net.stop()