import json
import os

class IP:
    def __init__(self,ipstr,prefix):
        #this class is used to calculate the ip used by ovs
        #ipstr eg:"169.254.1.1"
        self.ip=[0,0,0,0]
        temp=ipstr.split('.')
        assert len(temp)==4
        self.ip[0]=int(temp[0])
        self.ip[1]=int(temp[1])
        self.ip[2]=int(temp[2])
        self.ip[3]=int(temp[3])
        self.needAdd=2**(32-prefix)
        self.ans=[0,0,0,0]

    def next(self):
        #get the next ip,if wrong return None
        k=3
        while k>0:
            if self.ip[k]>255:
                temp=self.ip[k]//256
                self.ip[k]-=temp*256
                self.ip[k-1]+=temp
                k-=1
                continue
            break
        if self.ip[0]>255:
            return None
        for i in range(4):
            self.ans[i]=self.ip[i]
        self.ip[3]+=self.needAdd
        return self.ans



def clos(k):
    f2 = open('instruction/clos/' + str(k) + '.txt', 'w')
    netIP = IP("10.0.0.0", 24)
    f2.write("topo/clos/graph_clos_" + str(k) + ".json\n")
    f2.write("c hierarchy " + str(k) + "\n")
    f2.write("c a color\n")
    f2.write("c printf_op 0\n")
    f2.write("c print 0\n")
    f2.write("muti\n")
    for i in range(int(k * k / 2)):
        net = netIP.next()
        f2.write(f"net {i} a {net[0]}.{net[1]}.{net[2]}.{net[3]}/24\n")
    f2.write("/muti\n")
    f2.close()


def topology(name):
    f2=open('instruction/zoo/'+name+'.txt','w')
    netIP=IP("10.0.0.0",24)
    f2.write("topo/zoo/"  +name+ ".json\n")
    f2.write("c a greedy\n")
    f2.write("c printf_op 1\n")
    f2.write("c print 0\n")
    f2.write("muti\n")
    file=open("topo/zoo/"+name+".json",'r')
    file_content = file.read()
    content = json.loads(file_content)
    nodes = content['nodes']
    for i in range(len(nodes)):
        net = netIP.next()
        f2.write(f"net {i} a {net[0]}.{net[1]}.{net[2]}.{net[3]}/24\n")
    f2.write("/muti\n")
    f2.close()


# topology("Bellsouth")
# topology("Fccn")
# topology("Grnet")
# topology("GtsHungary")
# topology("GtsSlovakia")
# topology("Litnet")
# topology("RoEduNet")
# topology("Ulaknet")
# topology("Vinaren")
topology("Cogentco")