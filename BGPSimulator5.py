import numpy as np
import copy
import colorama
from queue import Queue
import random
import json
import os
import networkx as nx
import matplotlib.pyplot as plt
from bitarray import bitarray


'''
该程序希望将BGPSimulator4的功能拓展到多点发包
'''

#####utils######
def mycopy(list):
    if len(list) == 0:
        return []
    else:
        return copy.deepcopy(list)


def network_str_to_tuple(str):
    # str记录网络，类似于10.0.0.0/24，返回值类似于(167772160,24)
    temp = str.split('/')
    numbers = temp[0].split('.')
    ip = 0
    for i in range(4):
        ip *= 256
        ip += int(numbers[i])
    return (ip, int(temp[1]))


def tuple_to_network_str(tuple):
    numbers = [0, 0, 0, 0]
    temp = tuple[0]
    for i in range(4):
        numbers[3 - i] = temp % 256
        temp = temp // 256
    str = "{}.{}.{}.{}/{}".format(numbers[0], numbers[1], numbers[2], numbers[3], tuple[1])
    return str

def check_contain_network(net1,net2):
    #判断net1是否被net2包含，如果包含返回1，否则返回0
    if net1[1]>net2[1]:
        return 0
    temp1=net1[0]>>net1[1]
    temp2=net2[0]>>net2[1]
    if temp1==temp2:
        return 1
    else:
        return 0


def check_exist(path_list, node):
    # 看path list里面是否有node,如果有，返回它的下标
    if node in path_list:
        return path_list.index(node)
    else:
        return -1

def check_exist_numpy(path_list,node):
    # 看path list里面是否有node,如果有，返回它的下标
    if node in path_list:
        a=np.where(path_list==node)
        return a[0][0]
    else:
        return -1

def add(node1, node2):
    Nodes[node1].peer_list.append(node2)
    Nodes[node2].peer_list.append(node1)


def draw_picture(network,node):
    global G_final
    global draw_pos
    if G_final==None:
        G_final,draw_pos=draw_picture(network)
        plt.show(block=False)
        return None
    #G_final.remove_edge(node)
    # for item in Nodes[node].network_linked_nodes[network]:




def draw_picture(network):
    # 画图，将中间步骤画出，用于调试,但是有bug，目前图像会覆盖
    flag = 1
    if flag == 1:
        return None
    global draw_times
    #global draw_pos
    G_picture = nx.DiGraph()
    for i in range(MAX_NODE):
        G_picture.add_node(i, num=i)

    #if draw_pos == None:
    pos = nx.spring_layout(G_picture)

    for i in range(MAX_NODE):
        if network in Nodes[i].network_path:
            for item, value in Nodes[i].network_path[network].items():
                if len(value) == 0:
                    continue
                if item == Nodes[i].best_point[network]:
                    G_picture.add_edge(i, item, edge_color='red', linestyle='solid', alpha=1)
                else:
                    if G_picture.has_edge(item,i):
                        #有最优边
                        continue
                    G_picture.add_edge(i, item, edge_color='blue', linestyle='dotted', alpha=0.4)
                    G_picture.add_edge(item, i, edge_color='blue', linestyle='dotted', alpha=0.4)

    node_labels = nx.get_node_attributes(G_picture, 'num')
    nx.draw_networkx_labels(G_picture, pos, labels=node_labels)
    edges = nx.draw_networkx_edges(G_picture, pos, edgelist=G.edges())
    for u, v, edge_data in G_picture.edges(data=True):
        nx.draw_networkx_edges(G_picture, pos, edgelist=[(u, v)], edge_color=edge_data['edge_color'],
                               style=edge_data['linestyle'], alpha=edge_data['alpha'])
    #plt.savefig('check/' + str(draw_times) + '.png')
    draw_times += 1
    return G_picture,pos


def judge_mytopo_circle(node,mytopology):
    # 判断node节点在mytopology中是否形成环，如果形成了返回1、指向node的节点，没有返回0、根节点
    temp_node_np = np.zeros(MAX_NODE, dtype=np.int8)
    temp_node_np[node] = 1
    flag = 0
    temp_node = node
    temp_point_node = node
    while mytopology[temp_node] != -1:
        if mytopology[temp_node] == node:
            temp_point_node = temp_node
        temp_node = mytopology[temp_node]
        if temp_node_np[temp_node] == 0:
            temp_node_np[temp_node] = 1
        else:
            flag = 1
            if temp_point_node == node:
                return 1, None
            return 1, temp_point_node
    return 0, temp_node


def change_value_for_graph(network,node,nodes_type_np,value):
    #对于network，将nodes_type_np进行赋值，值为value，（例外是如果value为1，则原本是5的话，也可以当作1）
    temp_node_np=np.zeros(MAX_NODE,dtype=np.int0)
    #temp_node_np[node]=1
    #nodes_type_np[node] = value
    tempq = Queue()
    tempq.put(node)
    while not tempq.empty():
        q_top_node = tempq.get()
        if temp_node_np[q_top_node]==1:
            continue
        if value!=1 or nodes_type_np[q_top_node]!=5:
            nodes_type_np[q_top_node]=value
        temp_node_np[q_top_node]=1
        # 只用拓展子节点就行，因为反正是圈，最后绕下来，总会绕到的
        for item in Nodes[q_top_node].network_linked_nodes[network]:
            tempq.put(item)

class BGP_metric:
    def __init__(self, loc_pref, len_as_path):
        self.loc_pref = loc_pref
        self.len = len_as_path

    def __lt__(self, other):
        if self.len == 0:
            return True
        if other.len == 0:
            return False
        if self.loc_pref != other.loc_pref:
            return self.loc_pref < other.loc_pref
        else:
            return self.len > other.len

    def change(self, other):
        # 主要原因是没查到python里面咋重载=
        self.loc_pref = other.loc_pref
        self.len = other.len

    def len_pref(self):
        return self.loc_pref

    def len_as(self):
        return self.len


#####/utils######


class Node:
    def __init__(self, node, as_num, name="No name"):
        self.node_number = node  # 记录该节点在Nodes里面的编号，只是为了方便处理
        self.name = name
        self.as_num = as_num  # 它用于记录节点的AS号，它来代替node_number来判断是否成环
        ###
        ###目前准备下面只改变network path里面的path map值，即每条路径改用为AS号，而其他均用node number
        ###

        self.peer_list = []  # 记录连的对等体的node number
        self.network = set()  # 记录该点能够直连的网络，key：ip，类似于10.0.0.0/24，具体记录为(ip,mask)
        self.network_path = {}  # 记录该点能够到达的网络及路径，key：ip，类似于10.0.0.0/24，具体记录为(ip,mask)，value：path_map，记录每个对等体到终点的路径
        self.network_loc_pref = {}  # 记录该点对应某个网络所有对等体的loc_pref值，key：((ip,mask),peer)，value：loc_pref
        self.best_point = {}  # 记录最优路径需要走的对等体，key：ip，类似于10.0.0.0/24，具体记录为(ip,mask)，value：peer node number
        self.network_linked_nodes = {}  # 记录对于指定网络，指向该点的节点，具体记录为(ip,mask),value: set(), set里记录对应网络指向该点的节点  //该字典只用于greedy算法

        self.config={} #记录进入BGP节点时，过滤路由的规则，目前规则格式(access-list)为  key:peer, value: acl_map. //它一个优先级、一个邻居只能定义一个acl！！
        # acl_map的格式为：key:priority,value:[permit/deny,{network}]

        self.record_switch = False  # 0表明不用记录每次运行后的路由表，1表明要记录
        self.record_file = ""  # 它用于指定上述记录的文件地址

    def change_record(self, switch, path=''):
        self.record_switch = int(switch)
        if self.record_switch == 1:
            if path != '':
                self.record_file = path
            else:
                self.record_switch = 0
                print("record file error")
                return -1
        else:
            self.record_file = ''
        return self.record_switch

    def add_config(self,strs):
        if strs[0]=='access-list':
            #添加访问控制列表
            # strs格式：access-list {priority} permit/deny {network} for {peer}
            assert len(strs)==6
            priority=int(strs[1])
            peer=int(strs[5])
            if peer in self.config:
                acl_map=self.config[peer]
                if priority in acl_map:
                    print("[WARNING]:节点{}对邻居{}的ACL里优先级{}已经有了，重复定义会覆盖原先的值！".format(self.node_number, peer,priority))

                acl_map[priority] = [strs[2], network_str_to_tuple(strs[3])]
            else:
                self.config[peer]={priority:[strs[2],network_str_to_tuple(strs[3])]}

    def show_config(self):
        #该函数用于展示self.config里面的入站规则
        print("-----------入站规则-------------")
        for k,v in self.config.items():
            print("access-list {} {} {}".format(k,v[0],v[1]))
        print("--------------------------------")


    def add_network(self, str):
        # node为要处理的节点，str记录网络，类似于10.0.0.0/24
        key = network_str_to_tuple(str)
        self.network.add(key)
        # self.send_message(key,[self.node_number],[])
        self.send_message(key, [self.as_num], [])

    def delete_network(self, str):
        # node为要处理的节点，str记录网络，类似于10.0.0.0/24
        # 先简单的看network中有没有str对应网络来删除，以后如果有需求的话，可以细分网络删除，eg. delete 10.0.1.0/24，但我有网络10.0.0.0/16，需要细分来删除，目前先不考虑这些
        key = network_str_to_tuple(str)
        if key in self.network:
            self.network.remove(key)
            self.send_message(key, [], [])

    def delete_route(self,str):
        #str记录路由。类似于10.0.0.0/24，这个它跟delete_network不一样的点在于，它不是node本身发布的路由，而且通过其他节点更新得到的
        key=network_str_to_tuple(str)
        #删除相关路由
        if key in self.network_path:
            del self.network_path[key]
        if key in self.best_point:
            del self.best_point[key]
        #向其邻居发包
        self.send_message(key,[],[])

    def show_all_network(self):
        # 显示整个BGP表
        self.delete_unarrived_network()
        print("Node", self.node_number)
        for net in self.network:
            print(tuple_to_network_str(net), ' :\t\ti')
        for net in self.network_path:
            if net in self.best_point:
                point = self.best_point[net]
            else:
                point = -1
            peer_map = self.network_path[net]
            print(tuple_to_network_str(net), ' :\t\t')
            for peer, peer_list in peer_map.items():
                if peer == point:
                    print('\t', colorama.Fore.RED + str(peer) + ':' + str(peer_list) + colorama.Fore.WHITE)
                else:
                    print('\t', peer, ':', peer_list)

    def show_all_network_to_file(self, file_path):
        # 显示整个BGP表
        self.delete_unarrived_network()
        with open(file_path, 'a') as f:
            temp = "Node" + str(self.node_number)
            f.write(temp + '\n')
            for net in self.network:
                temp = tuple_to_network_str(net) + ' :\t\ti'
                f.write(temp + '\n')
            for net in self.network_path:
                if net in self.best_point:
                    point = self.best_point[net]
                else:
                    point = -1
                peer_map = self.network_path[net]
                temp = tuple_to_network_str(net) + ' :\t\t'
                f.write(temp + '\n')
                for peer, peer_list in peer_map.items():
                    if peer == point:
                        # print('\t',colorama.Fore.RED + str(peer) +':'+ str(peer_list) + colorama.Fore.WHITE)
                        temp = '\t' + str(peer) + ':' + str(peer_list) + '  ****'
                        f.write(temp + '\n')
                    else:
                        temp = '\t' + str(peer) + ':' + str(peer_list)
                        f.write(temp + '\n')

    def change_network_loc_pref(self, str, peer, loc_pref):
        # 修改loc_pref
        temp = network_str_to_tuple(str)  # network
        key = (temp, peer)
        self.network_loc_pref[key] = loc_pref
        if temp in self.best_point:
            origin_best_path = self.network_path[temp][self.best_point[temp]]
        else:
            origin_best_path = []
        judge = self.whether_send_message(temp, origin_best_path)
        if judge == 1:
            if temp in self.network_path and temp in self.best_point:
                path = self.network_path[temp][self.best_point[temp]]
                best_path = copy.deepcopy(path)
                # best_path.append(self.node_number)
                best_path.append(self.as_num)
            else:
                best_path = []

            self.send_message(temp, best_path, [])

    def check_whether_arrive(self, network):
        if network in self.network:
            return 1
        if network in self.network_path:
            temp = self.network_path[network]
            if temp == {}:
                return 0
            else:
                judge = 0
                record = []
                for peer, peer_list in temp.items():
                    if len(peer_list) > 0:
                        return 1
                    else:
                        record.append(peer)
                for peer in record:
                    del self.network_path[network][peer]
                return 0

    def delete_unarrived_network(self):
        # 同步，确保存储的信息是正确的
        record = []
        for net in self.network_path.keys():
            if self.check_whether_arrive(net) == 0:
                record.append(net)

        for i in record:
            del self.network_path[i]
            if i in self.best_point:
                del self.best_point[i]


    def whether_send_message(self, network, origin_path):
        # 判断是否需要发包，需要返回1，否则返回0
        # 这个是self.network_path改变以后运行的，看看是不是跟以前的oring_path一样，决定是不是变best_point，以及是否发包
        # 只针对该network的best_point，origin_path是原先最优路径,如果不存在就是空
        # 需要特判一下network直达的情况
        if network in self.network:
            # 直达
            if network not in self.network_path:
                # 没其他路走，不用变
                return 0
            else:
                peer_map = self.network_path[network]
                best_metric = BGP_metric(0, 0)
                best_node = -1
                for peer in peer_map.key():
                    temp = (network, peer)
                    if temp in self.network_loc_pref:
                        loc_pref = self.network_loc_pref[temp]
                    else:
                        loc_pref = 100
                    temp = BGP_metric(loc_pref, len(peer_map[peer]))
                    if best_metric < temp:  # and not check_exist(peer_map[peer],self.node_number):#应该不用，因为在修改时候就应该判断是否有环，而不是这时候判断
                        best_metric.change(temp)
                        best_node = peer
                if best_metric.loc_pref <= 100:
                    # 没高于直连的，不用变
                    return 0
                else:
                    self.best_point[network] = best_node
                    return 1

        # 下面的情况就是非直达了
        if network not in self.network_path:
            # 可能是删除掉该路由了
            if origin_path == []:
                # 如果原本就没有，改了以后还没有，就说明是一直没有，不用改
                return 0
            else:
                del self.best_point[network]
                return 1
        else:
            peer_map = self.network_path[network]
            judge = 0  # 判断peer_map是否为空
            for peer in peer_map:
                if len(peer_map[peer]) > 0:
                    judge = 1
                    break
            if judge == 0:
                if origin_path == []:
                    # 如果原本就没有，改了以后还没有，就说明是一直没有，不用改
                    return 0
                else:
                    del self.network_path[network]
                    del self.best_point[network]
                    return 1
            best_metric = BGP_metric(0, 0)
            best_node = -1
            for peer, peer_list in peer_map.items():
                temp = (network, peer)
                if temp in self.network_loc_pref:
                    loc_pref = self.network_loc_pref[temp]
                else:
                    loc_pref = 100
                temp = BGP_metric(loc_pref, len(peer_list))
                if best_metric < temp:  # and not check_exist(peer_map[peer],self.node_number):
                    best_metric.change(temp)
                    best_node = peer
            if best_node == -1:
                # 说明没更新
                return 0
            else:
                self.best_point[network] = best_node
                if self.network_path[network][best_node] == origin_path:
                    return 0
                else:
                    return 1

    def deal_mytopology(self, network, origin_node):
        # 用于处理当本节点被修改后，对应network下，mytopology等记录的节点的类型问题，其中origin_node是该节点原先的父节点（可能为-1）
        #   注意此时图已经被修改过去了，只需要修改对应自己这条线上的节点类型就行
        # 此时，由于没有待处理的节点集合，所以被它修改的节点类型只有1、2、3、5

        nodes_type_np = mytopo_nodes_type[network]
        #理论上在greedy函数时候就已经将mytopology给构建出来了
        assert network in alltopology
        mytopology =alltopology[network]
        # 一、对于origin_node一线的修改，只需要考虑是不是可能是环，然后被破开了
        # origin_node==-1说明该本节点原先没连东西，所以继续不用考虑这一线了
        if origin_node != -1:  # 说明需要考虑环
            if mytopology[self.node_number] == origin_node:  # 这个对应一个非常棘手的情况，目前只在环中遇到，即没断成，还是环
                # 如果是环的话，就应该把5标记向下传递，最好传给核心环上逆箭头方向的点
                # flag, _ = judge_mytopo_circle(self.node_number,mytopology)
                # if flag == 1:
                #     # 真的有环，找核心环上逆箭头方向的点
                #     temp_node = self.node_number
                #     nodes_type_np[temp_node] = 1
                #     while mytopology[temp_node] != self.node_number:  # 转一圈，找到这个点
                #         temp_node = mytopology[temp_node]
                #     nodes_type_np[temp_node] = 5
                #     # 由于旧的和新的一样，所以不用改了
                #     return None
                # else:
                #       #24-10-28:该情况由zoo中的BellSouth拓扑、多点发包情况爆出
                #     raise ValueError("出现了除环以外的情况，代码未处理！")
                ##24-10-28:这种情况我认为是父节点修改了自己的best-path，然后子节点会顺手继承父节点的best-path，而不变父节点，因此它可能在各种情况下见到。
                #此时由于父节点不变，因此如果父节点时deal_mytopology妥善处理了的话，这里应该不用处理
                return None
            # if nodes_type_np[origin_node]不为1、5，说明不是环，就不用处理这条线上的了
            if nodes_type_np[origin_node] == 1 or nodes_type_np[origin_node] == 5:  # 说明它原先位于一个圈里，要看是不是断开环了
                flag, _ = judge_mytopo_circle(origin_node,mytopology)
                if flag == 1:
                    # 说明还是有环
                    # 接下来需要区分是它连接到的新环是非核心节点（不参与构建环），还是核心节点（参与构建环）
                    temp_node_np = np.zeros(MAX_NODE, dtype=np.int8)
                    temp_node = self.node_number
                    temp_5_node = None
                    while temp_node_np[temp_node] != 1:
                        if mytopology[temp_node] == self.node_number:
                            temp_5_node = temp_node  # 它求出了如果本节点是核心节点，则它的上一个是谁
                        temp_node_np[temp_node] = 1
                        temp_node = mytopology[temp_node]
                    if temp_node != self.node_number:  # 说明绕了一圈，最终相见时不是本节点，即本节点是非核心节点，只需要改为1类型
                        nodes_type_np[self.node_number] = 1
                    else:  # 需要改为5类型
                        if temp_5_node == None:
                            raise ValueError("虽然找到了成环的罪魁祸首，但没找到5类型节点，有bug")
                        nodes_type_np[temp_5_node] = 5
                        nodes_type_np[self.node_number] = 1
                    # 由于它原本就有环，所以它的子孙节点都修改了，不用执行后面的了
                    return None

                else:  # 说明没环了，那就是断开环了，需要更改这一条线上的所有节点
                    tempq = Queue()
                    if origin_node==-2:
                        debug=1
                    tempq.put((origin_node, origin_node))
                    while not tempq.empty():
                        q_top_node, fa = tempq.get()
                        if nodes_type_np[q_top_node] == 3 or nodes_type_np[q_top_node] == 2:
                            continue
                        if mytopology[q_top_node] != -1:
                            nodes_type_np[q_top_node] = 3  # 说明该点是3类型，它上面有节点
                            tempq.put((mytopology[q_top_node], q_top_node))
                        else:
                            nodes_type_np[q_top_node] = 2

                        for item in Nodes[q_top_node].network_linked_nodes[network]:
                            if item == fa:
                                continue
                            tempq.put((item, q_top_node))

        # 二、考虑本节点的节点归属,如果有初始环，直接全线变为1
        # 如果它根本没连新边，那就直接跳到三
        flag_third = 0  # 它用于判断第三步是否需要执行，当生成5节点时就不需要执行
        if mytopology[self.node_number] == -1:
            nodes_type_np[self.node_number] = 2
        else:
            # 如果连了新边，则顺序考虑
            # 对于新线的修改，考虑是不是可能形成环，如果形成了一个初始环，则本节点是5；如果是连上了一个环，那么本节点是1。
            temp_fa = mytopology[self.node_number]
            if nodes_type_np[temp_fa] == 1 or nodes_type_np[temp_fa] == 5:  # 如果原来的节点就为环，那么本节点是1
                nodes_type_np[self.node_number] = 1
                flag,_=judge_mytopo_circle(temp_fa,mytopology)
                if flag==0:
                    raise ValueError("deal_mytopology第二步判环失误，原本无环，但是判断为有环了")
            else:  # 理论上，原来就没环了
                # 接下来判断是否可能形成了初始环
                flag, temp_point_node = judge_mytopo_circle(self.node_number,mytopology)
                if flag == 1:  # 说明有环，生成初始环了
                    # 此时说明self.node_number是改变的那个，指向它的节点就应该是5类型节点
                    flag_third = 1
                    assert  temp_point_node!=None# 如果temp_point_node为None，说明self.node_number为非核心节点，有bug
                    #下面的代码是遇到1或5就停止向下赋值，因为我原本认为它下面的值一定已经改了；但是这个不清楚是不是真的是这样
                    nodes_type_np[temp_point_node] = 5
                    tempq = Queue()
                    tempq.put(temp_point_node)  # 此处必须为temp_point_node，也就是5类型节点，因为如果不是，那么在遍历到5类型时就会中断
                    while not tempq.empty():
                        q_top_node = tempq.get()
                        # 只用拓展子节点就行，因为反正是圈，最后绕下来，总会绕到的
                        for item in Nodes[q_top_node].network_linked_nodes[network]:
                            if nodes_type_np[item] != 1 and nodes_type_np[item] != 5:  # 说明还没被修改
                                nodes_type_np[item] = 1
                                tempq.put(item)
                    #下面的注释就是假定上面不会赋值干净，所以全赋值一遍的操作
                    #change_value_for_graph(network, temp_point_node, nodes_type_np, 1)# 此处必须为temp_point_node，也就是5类型节点，因为如果不是，那么在遍历到5类型时就会中断
                    nodes_type_np[temp_point_node] = 5
                else:  # 说明没环，那本节点就是3
                    nodes_type_np[self.node_number] = 3

        # 三、对于本节点的子孙节点，在排除了环的可能性后，就单纯是树，节点全变成3；如果本节点为1，则后代全为1；如果为5，则上述已经改变了
        # if nodes_type_np[self.node_number]!=5:#如果不为5，说明这步还需要
        if flag_third != 1:  # r如果它等于1，则说明上面进入了生成5类型的代码中了，就不需要下面的赋值了
            # need_type就是它的子孙节点的类型
            if nodes_type_np[self.node_number] == 2:
                need_type = 3
            else:
                need_type = nodes_type_np[self.node_number]
            tempq = Queue()
            tempq.put(self.node_number)
            while not tempq.empty():
                q_top_node = tempq.get()
                for item in Nodes[q_top_node].network_linked_nodes[network]:
                    nodes_type_np[item] = need_type
                    tempq.put(item)


    def judge_whether_deal(self,message):
        #根据self.config判断是否要放行这个message。如果都不匹配，则默认放行
        #返回1表示放行，0表示不放行
        if message.from_node in self.config:
            acl_map=self.config[message.from_node]
        else:
            return 1
        sorted_keys = sorted(acl_map.keys())
        for key in sorted_keys:
            acl=acl_map[key]
            if check_contain_network(message.network,acl[1]):
                #表示它处于这个acl的控制中
                if acl[0]=='deny':
                    return 0
                elif acl[1]=='permit':
                    return 1
        return 1


    def deal_node(self, mode='normal'):
        # 处理node收到消息的函数
        deal_message_dup()
        origin_path_record = {}  # 记录某个网络的origin_path记录了没有，如果记录了，以后就不要记录，因为可能因为处理message时修改了network_path导致了变化
        for message in Message_list:
            if message.to_node == self.node_number and message.deal == 0:
                # 如果是直连的，看看loc_pref高不高，如果高就改（此时属于配置错误）；如果不高就不处理该message
                message.has_deal()

                #判断node是否有配置不放行这个message到BGP的流程中
                if self.judge_whether_deal(message)==0:
                    print("不放行的包：",message)
                    continue

                # ----！！！！-----需要模拟一下看看实际情况下这种是否会震荡，因为目前该程序配置错了就不会再管这个network了-----！！！！-----
                if message.network in self.network:  # 如果是直连
                    # 如果network直连
                    # if check_exist(message.path,self.node_number)==1:#该message中有该node，说明有环
                    if check_exist(message.path, self.as_num) != -1:  # 该message中有该node，说明有环
                        continue
                        # raise ValueError("{} is deleted by incorrect config".format(tuple_to_network_str(message.network)))
                    else:
                        if message.network not in origin_path_record:  # 如果origin_path_record没有记录，那么就需要记录
                            if message.network in self.best_point:  # 如果有best_point，那就记下
                                origin_path_record[message.network] = self.network_path[message.network][
                                    self.best_point[message.network]]
                            else:  # 如果没有，那就为空
                                origin_path_record[message.network] = []
                        self.network_path[message.network][message.from_node] = copy.deepcopy(message.path)
                    continue

                if message.network in self.network_path:  # 如果是多跳到达
                    # network不直连
                    # 记录原先的最优路径
                    if message.network not in origin_path_record:
                        if message.network in self.best_point:
                            origin_path_record[message.network] = self.network_path[message.network][
                                self.best_point[message.network]]
                        else:
                            origin_path_record[message.network] = []
                    # 处理message
                    # if check_exist(message.path, self.node_number) == 1:#如果message中包括自己，那么说明从该节点根本走不通
                    if check_exist(message.path, self.as_num) != -1:  # 如果message中包括自己，那么说明从该节点根本走不通
                        self.network_path[message.network][message.from_node] = []
                    else:
                        self.network_path[message.network][message.from_node] = copy.deepcopy(message.path)


                else:
                    # 原先就不通network
                    origin_path_record[message.network] = []
                    # if check_exist(message.path, self.node_number) == 0:
                    if check_exist(message.path, self.as_num) == -1:
                        # self.network_path[message.network][message.from_node]=[]
                        self.network_path[message.network] = {}
                        self.network_path[message.network][message.from_node] = copy.deepcopy(message.path)

        for network, origin_best_path in origin_path_record.items():
            judge = self.whether_send_message(network, origin_best_path)

            if judge == 1:
                # 以下是修改mytopology的拓扑
                flag_node_list = []
                assert network in alltopology
                mytopology = alltopology[network]
                if network in self.best_point:
                    if mode == 'normal':
                        mytopology[self.node_number] = self.best_point[network]
                    elif mode == 'greedy':  # 如果是我的算法，再执行下面的内容
                        # 修改mytopology和network_linked_nodes[network]的值
                        # 先将原先的父节点中network_linked_nodes记录的子节点删掉
                        temp_origin_node = mytopology[self.node_number]
                        if temp_origin_node != -1:
                            Nodes[temp_origin_node].network_linked_nodes[network].remove(self.node_number)
                        mytopology[self.node_number] = self.best_point[network]
                        # 再将现在连的父节点的network_linked_nodes中加入本节点
                        temp = self.best_point[network]
                        Nodes[temp].network_linked_nodes[network].add(self.node_number)
                        self.deal_mytopology(network, temp_origin_node)

                    flag_node = self.best_point[network]
                    flag_node_list.append(flag_node)
                else:
                    if mode == 'normal':
                        mytopology[self.node_number] = -1
                    elif mode == 'greedy':
                        # 修改mytopology和network_linked_nodes[network]的值
                        # 将原先的父节点中network_linked_nodes记录的子节点删掉
                        temp_origin_node = mytopology[self.node_number]
                        if temp_origin_node != -1:
                            Nodes[temp_origin_node].network_linked_nodes[network].remove(self.node_number)
                        mytopology[self.node_number] = -1
                        self.deal_mytopology(network, temp_origin_node)
                    # 下面的用于打标签，能否分辨这个节点操作未来是否可以省去（eg.空数据包送到空路由表时不用管）
                    for temp_node in self.peer_list:
                        if network not in Nodes[temp_node].best_point:
                            flag_node = temp_node
                            flag_node_list.append(flag_node)

                if network in self.network_path and network in self.best_point:
                    temp = self.network_path[network][self.best_point[network]]
                    best_path = copy.deepcopy(temp)
                    # best_path.append(self.node_number)
                    best_path.append(self.as_num)
                else:
                    best_path = []

                self.send_message(network, best_path, flag_node_list)
                #下面几行用于画图
                # if len(origin_best_path)>0:
                #     temp_draw_origin=origin_best_path[-1]
                # else:
                #     temp_draw_origin=None
                # if network in self.best_point:
                #     temp_draw_final=self.best_point[network]
                # else:
                #     temp_draw_final=None
                #draw_picture(network,self.node_number)

        if self.record_switch == 1:
            self.save_tracing_to_file()
        # raise ValueError("need to implement")

    def save_tracing_to_file(self):
        # 该函数用于记录节点每次执行后总体的路由表，方便调试
        with open(self.record_file, 'a')as f:
            temp = '-' * 30
            f.write(temp + '\n')
        for i in range(MAX_NODE):
            Nodes[i].show_all_network_to_file(self.record_file)

    def send_message(self, network, message, flag_node_list):  # 发送的message里已经包含自己的node number了
        for peer in self.peer_list:
            # 目前一个想法，当撤边时，如果对面已经为空了，那就说明自己向它发送的空包已经没用，就不用管
            # if len(message)==0:
            #     if Nodes[peer].check_whether_arrive(network)==0:#如果对面为空，说明它就是不正常的
            #         temp = Message(self.node_number, peer, network, message, 1)
            #     else:
            #         temp = Message(self.node_number, peer, network, message, 0)
            # #以下的代码仅考虑了加边的情况，当撤边时，A会向B发空，然后B向A也发空
            # #---！！！----
            # #这段代码有问题，如果A最优被断了，选择了B，但B也有一条备选选择A，就会导致A重新选了B，但没跟B说，因为它发给B的报文是[...,B,A]
            # #如果此时B最优也断了，选择了A，就会导致A和B都以为有一条路能到达终点
            # elif len(message)==1 or message[-2]!=peer:#正常的包
            #     temp = Message(self.node_number, peer, network, message,0)
            # else:
            #     temp = Message(self.node_number, peer, network, message, 1)
            if peer in flag_node_list:
                temp = Message(self.node_number, peer, network, message, 1)
            else:
                temp = Message(self.node_number, peer, network, message, 0)

            Message_list.append(temp)


class Message:
    def __init__(self, from_node, to_node, network, path, flag):
        self.from_node = from_node
        self.to_node = to_node
        self.network = network
        self.path = path
        self.deal = 0  # 为1代表它已经被处理了
        self.flag = flag  # 为0代表它是正常的一个包；为1代表它是从A发给B，然后B返给A的数据包，该数据包能够不处理

    def has_deal(self):
        self.deal = 1


def deal_message_dup():
    # 用于处理message list重复的问题
    delete = []
    message_map = {}
    for i in range(len(Message_list)):
        message = Message_list[i]
        if message.deal == 1:
            delete.append(i)
        else:
            if (message.from_node, message.to_node,message.network) in message_map:
                delete.append(message_map[(message.from_node, message.to_node,message.network)])
            message_map[(message.from_node, message.to_node,message.network)] = i

    delete.sort(reverse=True)
    for temp in delete:
        del Message_list[temp]

def show_message_to_node(node):
    #用来展示发往node节点的message有哪些
    print("------Messages---------")
    for i in range(len(Message_list)):
        message=Message_list[i]
        if message.deal==1:
            continue
        else:
            if message.to_node!=node:
                continue

            print("message from {}, network {},as path is {}".format(message.from_node,tuple_to_network_str(message.network),message.path))
    print("------------------------")


def waiting_deal_node_list():
    # 返回目前需要处理的node list；
    # 同时返回每个node对应的状态字典，即是否不是必须的（A发给B，B又发给A，此时A为非必须），此处的状态对应message里的flag
    deal_message_dup()
    temp = np.zeros(MAX_NODE, dtype=np.int16)
    temp2 = np.ones(MAX_NODE, dtype=np.int16)
    for message in Message_list:
        if message.deal == 1:
            continue
        temp[message.to_node] = 1
        if message.flag == 0:  # 如果是正常的包，那直接该为0，说明必须发，为1说明可以忽略
            temp2[message.to_node] = 0
    temp3 = np.where(temp == 1)
    temp4 = {}
    for i in temp3[0]:
        temp4[i] = temp2[i]
    return temp3[0], temp4

def waiting_deal_node_list_network(network):
    #返回在network下需要处理的node list:
    # 同时返回每个node对应的状态字典，即是否不是必须的（A发给B，B又发给A，此时A为非必须），此处的状态对应message里的flag
    deal_message_dup()
    temp = np.zeros(MAX_NODE, dtype=np.int16)
    temp2 = np.ones(MAX_NODE, dtype=np.int16)
    for message in Message_list:
        if message.deal == 1:
            continue
        if message.network!=network:
            continue
        temp[message.to_node] = 1
        if message.flag == 0:  # 如果是正常的包，那直接该为0，说明必须发，为1说明可以忽略
            temp2[message.to_node] = 0
    temp3 = np.where(temp == 1)
    temp4 = {}
    for i in temp3[0]:
        temp4[i] = temp2[i]
    return temp3[0], temp4

def get_all_network():
    net_map=set()
    for message in Message_list:
        net_map.add(message.network)
    return net_map

def waiting_deal_node_list_greedy():
    #该函数作用与waiting_deal_node_list相同，但是它用于新版的greedy方案，（可以是收到最多network的节点先发包，也可以是收到最多包的节点先发，这个可以再讨论）
    #目前greedy算法先采取最好写的，收到最多包的节点先发，这个包是(network,from_node)标识
    deal_message_dup()
    temp = np.zeros(MAX_NODE, dtype=np.int16)
    temp2 = np.ones(MAX_NODE, dtype=np.int16)
    net_map={}
    for message in Message_list:
        if message.deal == 1:
            continue
        #----下面的一段代码是统计总network---
        if message.to_node not in net_map:
            net_map[message.to_node]=set()
            net_map[message.to_node].add(message.network)
        else:
            if message.network not in net_map[message.to_node]:
                net_map[message.to_node].add(message.network)
                temp[message.to_node]+=1


        #----下面的一行代码是统计总发包------
        # temp[message.to_node] += 1
        if message.flag == 0:  # 如果是正常的包，那直接该为0，说明必须发，为1说明可以忽略
            temp2[message.to_node] = 0
    sorted_index=np.argsort(temp)
    # sorted_arr = np.flip(np.sort(temp))
    node_list=[]
    temp4={}
    for i in reversed(sorted_index):
        if temp[i]==0:
            break
        node_list.append(i)
        temp4[i]=temp2[i]
    # temp3 = np.where(sorted_arr >= 1)
    # temp4 = {}
    # for i in temp3[0]:
    #     temp4[i] = temp2[i]
    return node_list, temp4



def random_select_node(printf):
    # 使用随机的方法来进行选取节点
    select_node_list, node_flag_map = waiting_deal_node_list()
    length = len(select_node_list)
    if length == 0:
        return 0
    random_index = random.randrange(length)
    number = select_node_list[random_index]
    if number==2:
        debug=1
    Nodes[number].deal_node()
    operator_list.append((number, node_flag_map[number]))
    if printf == 1:
        Nodes[number].show_all_network()
    return 1

def manual_select_node(printf):
    #人工选择一个节点来执行
    select_node_list, node_flag_map = waiting_deal_node_list()
    print("待选择的节点有：",select_node_list)
    while 1:
        node=input("deal Node:")
        node=int(node)
        index = check_exist_numpy(select_node_list,node)
        if index!=-1:
            break
    Nodes[node].deal_node()
    operator_list.append((node,node_flag_map[index]))
    if printf==1:
        Nodes[node].show_all_network()
    return 1

def order_select_node(printf):
    #实际上就是直接一股脑直接select_node_list就行了，不用管其他顺序
    select_node_list, node_flag_map = waiting_deal_node_list()
    length = len(select_node_list)
    if length == 0:
        return 0
    for i in select_node_list:
        Nodes[i].deal_node()
        operator_list.append((i,node_flag_map[i]))
        if printf==1:
            Nodes[i].show_all_network()
    return 1

def greedy_select_node(printf):
    #实际上是order，但是考虑了收包多少的问题
    select_node_list, node_flag_map = waiting_deal_node_list_greedy()
    length = len(select_node_list)
    if length == 0:
        return 0
    choose_node=select_node_list[0]
    # print(choose_node)
    Nodes[choose_node].deal_node()
    operator_list.append((choose_node, node_flag_map[choose_node]))
    if printf == 1:
        Nodes[choose_node].show_all_network()
    return 1

def coloring_select_node(printf):
    global G
    # 先使用图着色的方法，得到不同颜色的节点，然后分别执行不同的颜色
    select_node_list, node_flag_map = waiting_deal_node_list()
    length = len(select_node_list)
    if length == 0:
        return 0

    # 构建子图
    Gtemp = nx.subgraph(G, select_node_list)
    # 计算不同节点的颜色，得到的是一个字典，每个节点对应一个数字代表一组
    temp = nx.coloring.greedy_color(Gtemp, strategy="DSATUR")
    # 求每个颜色的节点列表
    items = temp.items()
    value_to_keys_dict = {value: [key for key, _ in items if _ == value] for value in set(temp.values())}
    for dict_index in value_to_keys_dict:
        # 执行每个颜色的节点集合
        waiting_to_deal_list = value_to_keys_dict[dict_index]
        for temp_element in waiting_to_deal_list:
            # 顺序执行每个颜色里面的节点
            Nodes[temp_element].deal_node()
            operator_list.append((temp_element, node_flag_map[temp_element]))
            if printf == 1:
                Nodes[temp_element].show_all_network()
    return 1


class Greedy:
    def __init__(self):
        self.topology = np.zeros(MAX_NODE, dtype=np.int32)
        self.q = Queue()
        self.printf = 0  # 如果等于1，就打印中间结果，否则不打印
        self.node3v=3
        self.node5v=5
        self.node2v=1

    def change_printf(self, x):
        if x == 0 or x == 1:
            self.printf = x

    def judge_node_type_v2(self, node_list):
        # 返回所有节点的type和所有节点的best node，type表示下文的节点分类；best node表示当前list中应该选的最优节点
        nodes_type = np.zeros(len(node_list), dtype=np.int32)
        nodes_best = np.zeros(len(node_list), dtype=np.int32)
        for i in range(len(node_list)):
            node = node_list[i]
            if mytopology[node] == -1:  # 如果没有父节点，则为2类
                nodes_type[i] = 2
                nodes_best[i] = node
                continue
            if nodes_type[i] != 0:  # 如果已经判断出了类型，就不再重新判断
                continue
            # 下面开始向上走，找祖先节点，或者找是圈的证据
            now_node = node  # now_node表示走到哪个节点了
            best_node = node
            temp_list = [node]
            while 1:
                temp_node = mytopology[now_node]
                if temp_node == -1:  # 它就为fa*
                    if now_node in node_list:
                        best_node = now_node
                        type = 3
                    else:
                        type = 4
                    # 把路上在node list里面的所有节点全记下fa*
                    nodes_type[i] = type
                    nodes_best[i] = best_node
                    for j in range(len(temp_list)):
                        if temp_list[j] in node_list:
                            temp_index = np.where(node_list == temp_list[j])
                            rubbish = temp_index[0]
                            nodes_type[rubbish] = type
                            nodes_best[rubbish] = best_node
                    break

                if temp_node in node_list:  # 该父节点在node list里面，则需要记录下来，并继续向上走
                    temp_index = np.where(node_list == temp_node)
                    rubbish = temp_index[0]
                    if nodes_type[rubbish] != 0:  # 判断下是否已经判断出类型了，如果判断出了，直接用就好
                        if nodes_type[rubbish] == 2:  # 它是个独立节点，所以fa就是它
                            type = 3
                            best_node = temp_node
                        else:  # 否则为3、4类节点，说明已经找到fa*了，直接用就好
                            type = nodes_type[rubbish]
                            best_node = nodes_best[rubbish]
                        nodes_type[i] = type
                        nodes_best[i] = best_node
                        for j in range(len(temp_list)):
                            if temp_list[j] in node_list:
                                temp_index = np.where(node_list == temp_list[j])
                                rubbish = temp_index[0]
                                nodes_type[rubbish] = type
                                nodes_best[rubbish] = best_node
                        break

                # 以下没判断出类型，所以老老实实判断类型
                # 以下说明该父节点不在node list里面
                if temp_node in temp_list:  # 是个环，type为1
                    nodes_type[i] = 1  # type
                    nodes_best[i] = best_node
                    for j in range(len(temp_list)):
                        if temp_list[j] in node_list:
                            temp_index = np.where(node_list == temp_list[j])
                            rubbish = temp_index[0]
                            # rubbish = node_list.index(temp_list[j])
                            nodes_type[rubbish] = 1  # type
                            nodes_best[rubbish] = best_node
                    break
                now_node = temp_node
                if now_node in node_list:  # and self.node_fa[now_node] == 0:
                    best_node = now_node
                temp_list.append(now_node)
        return nodes_type, nodes_best
        # raise ValueError("need to implement")

    def cal_node_type_v3(self, network):
        # 此时所有的节点类型还没有定，需要重新计算
        nodes_type_np = mytopo_nodes_type[network]
        assert network in alltopology
        mytopology = alltopology[network]
        for i in range(MAX_NODE):
            if nodes_type_np[i] != 0:  # 说明已经定好了，直接跳
                continue
            if mytopology[i] == -1:  # 说明是2类型
                nodes_type_np[i] = 2
                tempq = Queue()
                tempq.put(i)
                while not tempq.empty():
                    q_top_node = tempq.get()
                    for item in Nodes[q_top_node].network_linked_nodes[network]:
                        nodes_type_np[item] = 3
                        tempq.put(item)
            else:  # 说明有父节点
                # 进行判环,理论上不应该有环，直接梭哈一把
                flag, temp_node = judge_mytopo_circle(i,mytopology)
                if flag == 1:
                    raise ValueError("cal_node_type_v3中发现有环，代码有bug！")
                if flag == 1:  # 找到环了
                    tempq = Queue()
                    tempq.put(i)
                    while not tempq.empty():
                        q_top_node = tempq.get()
                        if nodes_type_np[q_top_node] == 1:  # 说明已经赋值过了，不同get了
                            continue
                        nodes_type_np[q_top_node] = 1
                        # 不用搜父节点，因为反正是环，绕一圈就是子节点了
                        for item in Nodes[q_top_node].network_linked_nodes[network]:
                            tempq.put(item)
                else:
                    # 没找到环，说明此时找到了树
                    nodes_type_np[temp_node] = 2
                    tempq = Queue()
                    tempq.put(temp_node)
                    while not tempq.empty():
                        q_top_node = tempq.get()
                        for item in Nodes[q_top_node].network_linked_nodes[network]:
                            nodes_type_np[item] = 3
                            tempq.put(item)

    def judge_node_type_v3(self, node_list, network):
        # 返回所有节点的type和所有节点的best node，type表示下文的节点分类；best node表示当前list中应该选的最优节点
        # 此时由于deal_mytopology的执行，节点类型已经基本定型，此处是为了排除不在node_list中的节点的
        # 同时，不在区分3、4类型的区别，因为两者执行时被同等对待
        # 所以，只有将节点类型变为0（5最好不要变0，防止环中没5；但是理论上不应该出现这种情况，所以我还是变了，到时候报错时小心点）
        nodes_type_np = mytopo_nodes_type[network]
        check_5_node_list = np.where(nodes_type_np == 5)
        # assert len(nodes_type_np.shape) == 1
        node_types = np.copy(nodes_type_np)

        assert network in alltopology
        mytopology=alltopology[network]
        # 下面一段代码将node_list以外的node全赋值为0
        j = 0
        for i in range(MAX_NODE):
            if j >= len(node_list):
                node_types[i] = 0
                continue
            if i != node_list[j]:
                node_types[i] = 0
            else:
                j += 1
        for i in check_5_node_list[0]:
            if node_types[i] == 0:
                raise ValueError("将5类型节点变成0了，应该是bug")

        # 此时node_types就已经求出来了，接下来求best_nodes
        best_nodes = np.full(MAX_NODE, -1, dtype=np.int32)
        for i in range(MAX_NODE):
            if best_nodes[i] != -1:  # 说明已经赋值了，直接跳过
                continue
            if node_types[i] == 0:  # 不用考虑
                continue
            elif node_types[i] == 1 or node_types[i] == 5:  # 到一个环里，找到5. 理论上，5节点必须在node list里
                # 理论上，5必须在圈里，不可能在旁支，所以直接一路找fa就行
                temp_node_np = np.zeros(MAX_NODE, np.int0)
                temp_node_np[i] = 1
                temp_node = i
                while mytopology[temp_node] != -1:
                    if nodes_type_np[temp_node] == 5:  # 找到5了，不改了
                        final_node_5 = temp_node
                        break
                    temp_node = mytopology[temp_node]
                    if temp_node_np[temp_node] == 1:  # 转了一圈，但是还没有5，直接报错
                        raise ValueError("judge_node_type_v3找到环时，在核心的环中没找到5类型的节点")
                    temp_node_np[temp_node] = 1

                # 接下来将属于该环的节点的best node全赋值为final_node_5,直接只找子节点就行，因为反正是环，转一圈就是子节点了
                tempq = Queue()
                tempq.put(i)
                while not tempq.empty():
                    q_top_node = tempq.get()
                    best_nodes[q_top_node] = final_node_5
                    for item in Nodes[q_top_node].network_linked_nodes[network]:
                        if best_nodes[item] != final_node_5:  # 需要修改，所以加进去queue
                            tempq.put(item)

            elif node_types[i] == 2:
                best_nodes[i] = i
            elif node_types[i] == 3:
                temp_node = i
                final_node_3 = -1
                while mytopology[temp_node] != -1:
                    if node_types[temp_node] != 0:  # 说明在node list中
                        final_node_3 = temp_node
                    temp_node = mytopology[temp_node]
                if node_types[temp_node] != 0:  # 说明在node list中
                    final_node_3 = temp_node
                tempq = Queue()
                tempq.put(final_node_3)
                best_nodes[final_node_3] = final_node_3
                while not tempq.empty():
                    q_top_node = tempq.get()
                    for item in Nodes[q_top_node].network_linked_nodes[network]:
                        if best_nodes[item] == -1 and node_types[item] != 0:
                            best_nodes[item] = final_node_3
                        tempq.put(item)

        return node_types, best_nodes

    '''
    继续改写：
    新原则：
    1、每次都考虑目前能跑的所有节点
    2、每次如果有fa，就不考虑child
    3、延迟没有fa的
    //4.先不要断环，尽量能先断旁边的线就断旁边的线（防止以后出现环）//有待论证
    5.断环时，倒着往前断
        => (目前打算的顺序，先上5，再上3、4，实在没东西上2)
    #待处理的节点分类：  -1、有问题的
        #                   0、不用处理
        #                   1、有环的，上述破环方法
        #                   2、无fa的，直接断
        #                   3、有fa*的，但fa*在节点里的，断
        #                   4、有fa*的，但fa*不在节点里的，应该可以直接跑
        #                   5、在环内，但是由于曾经造成成环的最后一步选的是节点A，那么该节点就是节点A的父节点（逆箭头方向）
    '''

    def greedy_select_node_all(self):
        #该函数考虑了多点发包的，
        #贪心方法：原始贪心只考虑一点发包，现在多点时，对每个network找要发包的点，按照他们不同类型，以及出现的次数、数量进行换算，得到得分，然后选择最优节点执行
        net_set=get_all_network()

        if len(net_set)==0:
            return 0

        for network in net_set:
            if network not in alltopology:
                alltopology[network]=np.zeros(MAX_NODE, dtype=np.int32)
                mytopology=alltopology[network]
                # 建图，同时使用set记录有谁的父节点连接到本节点
                for node in range(MAX_NODE):
                    if network not in Nodes[node].network_linked_nodes:
                        Nodes[node].network_linked_nodes[network] = set()
                    if network in Nodes[node].best_point:
                        mytopology[node] = Nodes[node].best_point[network]
                        Nodes[mytopology[node]].network_linked_nodes[network].add(node)  # 理论上这个是不需要的，因为原先就会将这个修改正确
                    else:
                        mytopology[node] = -1

            if network not in mytopo_nodes_type:
                mytopo_nodes_type[network] = np.zeros(MAX_NODE, dtype=np.int8)  # 新建该network的节点类型记录表
                # mytopo_nodes_best[network]=np.zeros(MAX_NODE,dtype=np.int32)#新建该network的best node表

        node_value=np.zeros(MAX_NODE, dtype=np.int16)
        node_1=np.zeros(MAX_NODE, dtype=np.int16)#记录net_value里是否有值，代表该节点是需要执行的，如果有赋值为1
        for net in net_set:
            net_value=self.greedy_select_node_v3(net,0)#得到了net对应的每个点的权重
            condition = net_value >= 1
            node_1[condition]=1
            # 使用np.where来根据条件修改A的值
            node_value = np.where(net_value > 1, node_value + net_value, node_value)
        node_value=np.maximum(node_value,node_1)

        best_node = node_value.argmax()
        print(best_node)
        # 以下三行是执行
        Nodes[best_node].deal_node(mode='greedy')
        # draw_picture(network)
        operator_list.append((best_node, 0))#第二个参数原本是flag，用于标记这个包是否用处理的（因为携带了过时的信息），但是由于多个net，就没法识别它了，因为不同net，它不一定一样
        if self.printf == 1:
            Nodes[best_node].show_all_network()
        return 1

    def greedy_select_node_v3(self, network, origin_node):
        # global mytopo_nodes_type
        #该assert是用于判断是不是误使用了greedy，因为目前多节点的版本没有greedy算法
        # print("greedy_select_node_v3")
        assert network != None

        assert network in alltopology
        # 先提前把node type计算一遍
        self.cal_node_type_v3(network)
        # 破边，待处理的节点用queue记录
        return_value = np.zeros(MAX_NODE, dtype=np.int8)
        select_node_list, node_flag_map = waiting_deal_node_list_network(network)
        if len(select_node_list) != 0:
            nodes_type, nodes_best = self.judge_node_type_v3(select_node_list, network)

            for i in range(len(nodes_type)):
                if nodes_type[i]==2 and return_value[nodes_best[i]]<self.node2v:
                    return_value[nodes_best[i]]=self.node2v
                elif nodes_type[i]==3 and return_value[nodes_best[i]]<self.node3v:
                    return_value[nodes_best[i]] = self.node3v
                elif nodes_type[i]==5 and return_value[nodes_best[i]]<self.node5v:
                    return_value[nodes_best[i]] = self.node5v

        return return_value



    '''
    改写，需考虑几个原则
    1、每次都考虑目前能跑的所有节点(目前打算的顺序，先上1，再上3、4，实在没东西上2)
    2、每次如果有fa，就不考虑child
    3、延迟没有fa的
    '''

    def greedy_select_node_v2(self, network, origin_node):
        # 待处理的节点分类：  -1、有问题的
        #                   0、不用处理
        #                   1、有环的，上述破环方法
        #                   2、无fa的，直接断
        #                   3、有fa*的，但fa*在节点里的，断
        #                   4、有fa*的，但fa*不在节点里的，应该可以直接跑

        # 建图
        for node in range(MAX_NODE):
            if network in Nodes[node].best_point:
                mytopology[node] = Nodes[node].best_point[network]
            else:
                mytopology[node] = -1

        # 破边，待处理的节点用queue记录
        select_node_list, node_flag_map = waiting_deal_node_list()
        while not self.q.empty() or len(select_node_list) != 0:
            if self.q.empty():  # 执行队列空了，但是实际上待处理的节点未空，找目前能处理的节点进行处理
                nodes_type, nodes_best = self.judge_node_type_v2(select_node_list)
                '''以下代码是原本算法使用的'''
                nodes_need_deal = np.where(nodes_type == 1)
                if nodes_need_deal[0].size == 0:
                    nodes_need_deal = np.where(nodes_type > 2)
                    if nodes_need_deal[0].size == 0:
                        nodes_need_deal = np.where(nodes_type == 2)

                '''以下代码是分析上述顺序是否能调换，有什么影响的，做实验进行记录'''
                # 首先是 1 | 2 | 3、4
                # nodes_need_deal = np.where(nodes_type == 1)
                # if nodes_need_deal[0].size == 0:
                #     nodes_need_deal = np.where(nodes_type == 2)
                #     if nodes_need_deal[0].size == 0:
                #         nodes_need_deal = np.where(nodes_type > 2)
                # 其次是 2  | 34 | 1
                # nodes_need_deal = np.where(nodes_type == 2)
                # if nodes_need_deal[0].size == 0:
                #     nodes_need_deal = np.where(nodes_type > 2)
                #     if nodes_need_deal[0].size == 0:
                #         nodes_need_deal = np.where(nodes_type == 1)
                temp = set()
                for i in nodes_need_deal[0]:
                    temp.add(nodes_best[i])

                for node in temp:
                    self.q.put(node)

            # 执行队列没空，直接执行就行
            best_node = self.q.get()
            # 以下三行是执行
            Nodes[best_node].deal_node()
            operator_list.append((best_node, node_flag_map[best_node]))
            if self.printf == 1:
                Nodes[best_node].show_all_network()
            # temp_origin_node = mytopology[best_node]
            # if network in Nodes[best_node].best_point:
            #     mytopology[best_node] = Nodes[best_node].best_point[network]
            # else:
            #     mytopology[best_node] = -1
            select_node_list, node_flag_map = waiting_deal_node_list()

        # raise ValueError("need to reimplement")

class BFS:
    def __init__(self):
        self.record={}#记录每个network中，每个node的权重，第k层扩展就为k
        self.printf = 0  # 如果等于1，就打印中间结果，否则不打印
        self.node_num=np.zeros(MAX_NODE,dtype=np.int32)#它记录了每个节点在待执行列表中出现的权重累加，越小越优先（因为越小说明距离节点越近）
        self.list=[]#它记录了要执行的节点顺序
        self.MAX=1000#它用来计算第k层的权重，因为权重比较条件：1、如，i>j，则w(i)<w(j);2、w(i)>0;3、w(i)的变化要明显一些，最好不要log；且最好要int

    def cal_w(self,n):
        #计算第n层的权重
        if n>=self.MAX:
            return 1
        return self.MAX-n

    def init(self):
        #这个函数用来通过Massage_list中的值来反向退出record的值
        #具体就是查看message的network，知道改哪个network，然后标记from_node为已执行，to_node为待执行；0代表没有它，k代表第k层，-1代表执行过它了
        net_set = get_all_network()
        self.node_num = np.zeros(MAX_NODE, dtype=np.int32)

        for network in net_set:
            self.record[network]=np.zeros(MAX_NODE, dtype=np.int8)
        for message in Message_list:
            assert message.deal==0#理论上这个函数是刚开始就调用的，不应该有message被处理
            self.record[message.network][message.from_node]=-1
            self.record[message.network][message.to_node]=1
            self.node_num[message.to_node]+=self.cal_w(1)#这里之所以是-1，是因为这里第1层权重最大，然后还需要能够累加，就只能-

    def change_num(self,node):
        #该函数用于模拟，当选则了node以后，如何更改node_num
        for network in self.record:
            if self.record[network][node]<1:#如果它不在待处理序列中，不管它
                continue
            origin_value=self.record[network][node]
            self.record[network][node]=-1#如果它在，更新为已处理
            self.node_num[node]-=self.cal_w(origin_value)
            #接下来将其邻居更新到待处理列表中
            for peer in Nodes[node].peer_list:
                if self.record[network][peer]==0:
                    self.record[network][peer]=origin_value+1
                    self.node_num[peer]+=self.cal_w(origin_value+1)


    def get_exec_list(self):
        #这个函数用来得到执行序列
        #具体来说就是，通过统计每个to_node的个数，确定下一个要执行的节点
        while 1:
            # final=np.argmin(self.node_num[self.node_num>0])
            final=np.argmax(self.node_num)
            if self.node_num[final]==0:
                break
            self.list.append(final)
            self.change_num(final)


    def run(self,printf):
        #该函数执行所有逻辑：
        #先init，然后get exec list，然后按照list执行；最后执行完以后，可能会有其他点，此时按照greedy-data的贪心方法处理
        self.init()
        self.get_exec_list()
        print("BFS计算得到的处理序列为,",len(self.list),":",self.list)
        for i in self.list:
            select_node_list, node_flag_map = waiting_deal_node_list()
            assert i in select_node_list
            Nodes[i].deal_node()
            operator_list.append((i, node_flag_map[i]))
            if printf == 1:
                Nodes[i].show_all_network()

        while greedy_select_node(printf) == 1:
            continue



class Clos_hierarchy:
    def __init__(self,k):
        k=k
        self.stage = 0
        self.cal_end(k)


    def cal_end(self,k):
        #该函数用于计算clos不同层的边界
        self.first_end=int(k*k/2)
        self.second_end=k*k

    def hierarchy_select_node(self,printf):
        select_node_list, node_flag_map = waiting_deal_node_list()
        length = len(select_node_list)
        if length == 0:
            return 0
        final_node_index=0
        flag=0
        if self.stage==0:
            #执行第二层
            for i in range(len(select_node_list)):
                if select_node_list[i]>=self.first_end and select_node_list[i]<self.second_end:
                    final_node_index=i
                    flag=1
                    break
            if flag==0:
                self.stage+=1
        elif self.stage==1:
            #执行第三层
            for i in range(len(select_node_list)):
                if select_node_list[i]>=self.second_end :
                    final_node_index=i
                    flag=1
                    break
            if flag==0:
                self.stage+=1
        elif self.stage==2:
            #重执行第二层
            for i in range(len(select_node_list)):
                if select_node_list[i]>=self.first_end and select_node_list[i]<self.second_end:
                    final_node_index=i
                    flag=1
                    break
            if flag==0:
                self.stage+=1
        elif self.stage==3:
            #执行第一层
            for i in range(len(select_node_list)):
                if select_node_list[i] <self.first_end :
                    final_node_index = i
                    flag = 1
                    break
            if flag == 0:
                self.stage += 1
        elif self.stage==4:
            #有价值的节点都被执行完了，理论上可以随机执行了，因为这里第二三层节点会全被执行仅一次
            return random_select_node(printf)
        if flag==1:
            number = select_node_list[final_node_index]
            Nodes[number].deal_node()
            operator_list.append((number, node_flag_map[number]))
            if printf == 1:
                Nodes[number].show_all_network()
        return 1

def init_alltopology():
    #这个函数主要是为了初始化alltopology，为了除greedy-topo以外的其他方法，因为deal_node里面有用到mytopology，但是我只在greedy-topo里面初始化了，所以为了让其他能够运行，我弄了这个代码
    net_set = get_all_network()

    for network in net_set:
        if network not in alltopology:
            alltopology[network] = np.zeros(MAX_NODE, dtype=np.int32)

class Operator:
    def __init__(self):
        self.type ='greedy-topo'  # 'manual'#'random'#'greedy'    #random表示随机选取节点执行，greedy表示使用自己的贪心算法处理,#color表示每次使用图着色算法来处理
        self.greedy = Greedy()
        self.clos_hierarchy=Clos_hierarchy(10)
        self.bfs=BFS()
        self.code = []  # 用于记录脚本，为字符串数组,以EOF结尾
        self.fortime = 0
        self.printf = 0  # 如果等于0，则表明中间结果不打印
        self.printf_op = 0  # 如果等于0，则表明最后的operator list不打印，只打印其长度
        self.origin_operator_list=[]#它用来记录原先的operator list
        self.ifMuti = 0 #如果等于0，表示它不处于muti的状态，那么就一条指令执行完以后要选节点执行，等于1表示它处于muti状态，需要等所有muti里面的指令全完了以后再处理

    def select_node(self, network=None, node=None):
        if self.type=='bfs':
            init_alltopology()
            self.bfs.run(self.printf)
        elif self.type == 'random':
            init_alltopology()
            while random_select_node(self.printf) == 1:
                continue
        elif self.type == 'greedy-data':
            init_alltopology()
            # self.greedy.change_printf(self.printf)
            # self.greedy.greedy_select_node_v3(network, node)
            while greedy_select_node(self.printf)==1:
                continue
        elif self.type == 'greedy-topo':
            self.greedy.change_printf(self.printf)
            while self.greedy.greedy_select_node_all()==1:
                continue

        elif self.type == 'color':
            init_alltopology()
            while coloring_select_node(self.printf) == 1:
                continue
        elif self.type=='order':
            init_alltopology()
            while order_select_node(self.printf)==1:
                continue
        elif self.type=='manual':
            init_alltopology()
            while manual_select_node(self.printf)==1:
                continue
        elif self.type=='clos':
            init_alltopology()
            while self.clos_hierarchy.hierarchy_select_node(self.printf)==1:
                continue

    def show_operator_list(self):
        print("\noperator times:{} ".format(len(self.origin_operator_list)), end=' ')
        # print("{}次操作 ".format(len(operator_list)), end=' ')
        if self.printf_op == 0:
            print(" ")
            return None
        for element in self.origin_operator_list:
            if element[1] == 0:  # 正常的处理
                print("{}".format(element[0]), end=' ')
            elif element[1] == 1:  # 实际上可以忽略的包
                print(colorama.Fore.RED + str(element[0]) + colorama.Fore.WHITE, end=' ')
        print(" ")
        # print("{} 次操作".format(len(operator_list)), operator_list)

    def deal_input(self, data):
        global operator_list
        temp = data.split()
        if len(temp)==0:
            return None

        if temp[0]=='add' or temp[0]=='a':
            node=int(temp[1])
            Nodes[node].add_config(temp[2:])

        if temp[0]=='change' or temp[0]=='c':
            if temp[1]=='algorithm' or temp[1] == 'a':
                if temp[2] == 'random' or temp[2] == 'greedy-topo' or temp[2]=='greedy-data' or temp[2] == 'color' or temp[2] == 'manual' \
                        or temp[2] == 'order' or temp[2]=='clos' or temp[2]=='bfs':
                    self.type = temp[2]
                    print("algorithm has been changed as ", self.type)
            elif temp[1]=='printf':
                self.printf=int(temp[2])
                print("printf flag has been changed as ",self.printf)
            elif temp[1]=='printf_op':
                self.printf_op=int(temp[2])
                print("printf_op flag has been changed as ", self.printf_op)
            elif temp[1]=='hierarchy':
                self.clos_hierarchy=Clos_hierarchy(int(temp[2]))

        elif temp[0] == 'exit' or temp[0] == 'e':  # 结束
            exit(0)

        elif temp[0] == 'help' or temp[0] == 'h':
            print("add/a :增加BGP入站配置")
            print("\t ~ {node} access-list {priority} permit/deny {network} for {neighbor}: 添加acl访问控制列表，优先级越小表示越在前面匹配")
            print("change/c :修改配置")
            print("\t ~ algorithm/a [random/color/manual/order/greedy-data/greedy-topo] :用于选择算法，是随机(random),图着色(color),手动选择(manual)，顺序选择(order)")
            print("\t ~ printf [0/1] ：修改printf的值，0表示不打印中间过程，1表示打印。//中间过程指每执行一个节点后它的路由表")
            print("\t ~ printf_op [0/1] :修改printf_op的值，0表示最后的执行节点队列不打印，只打印其长度；1表示要都要打印")
            print("exit/e: 结束")
            print("loc_pref/loc {node} {peer} {network} {loc_pref} :用于修改loc_pref")
            print("\t node:int,peer:int,network:同上,loc_pref:int")
            print("network/net {node} [a/d] {network} :用于添加或删除网络，目前不支持删除或添加范围不同的（即+10.1.0.0/16,-10.1.1.0/24不支持）")
            print("\t node:int, a/d控制添加add和删除delete，network:格式同10.0.0.0/24")
            print("muti \n {codes} \n /muti :用于在这一时刻执行多条指令，指令最好为network的增减，loc_pref的修改，因为其他可能会出bug，而且其他指令没有在同一时刻执行的需求")
            print("record [0/1] {file_path}：中间步骤记录")
            print("route/r {node} d {network}：用于删除一个节点中记录的路由")
            print("show/s ：显示信息")
            print("\t ~ network/net {node}:显示node能到达的网络")
            print("\t ~ network/net all:显示所有节点能到达的网络")
            print("\t ~ operator/o:输出目前为止的操作序列")
            print("\t ~ config/c:输出配置")
            print("\t ~ messages/m {node}:输出发向node节点的所有包")
            print("\t ~ messages/m all:输出发向所有节点的所有包")
            print("\t ~ rule {node}:显示node的入站规则")
            print("shell/sh {times}  \n {codes} :用于循环执行代码")
            print("\t times:int,次数；codes:代码")
            #print("next/n {node}:用于在manual模式下，选择下一个要执行的节点")
            print("waiting/wait :输出待执行序列")

        elif temp[0] == 'loc_pref' or temp[0] == 'loc':  # 改变loc_pref
            if len(temp) != 5:
                return None
            # temp 0:loc  1:node  2:peer  3:network  4:loc_pref
            node = int(temp[1])  # 待改变的节点
            peer = int(temp[2])  # node的对等体
            Nodes[node].change_network_loc_pref(temp[3], peer, int(temp[4]))
            if self.ifMuti==0:
                self.select_node(network_str_to_tuple(temp[3]), node)
                self.origin_operator_list = operator_list
                self.show_operator_list()
                # print("{} 次操作".format(len(operator_list)), operator_list)
                operator_list = []

        elif temp[0]=='muti':
            self.ifMuti=1


        elif temp[0] == 'network' or temp[0] == 'net':
            if len(temp) != 4:
                return None
            # temp  0:net  1:node  2:a/d  3:network
            node = int(temp[1])
            if temp[2] == 'add' or temp[2] == 'a':  # 加一个network
                Nodes[node].add_network(temp[3])
            elif temp[2] == 'delete' or temp[2] == 'd':  # 删除一个network
                Nodes[node].delete_network(temp[3])
            if self.ifMuti==0:
                self.select_node(network_str_to_tuple(temp[3]), node)
                self.origin_operator_list=operator_list
                self.show_operator_list()
                # print("{} 次操作".format(len(operator_list)), operator_list)
                operator_list = []


        elif temp[0] == 'next' or temp[0] == 'n':
            Nodes[int(temp[1])].deal_node()
            Nodes[int(temp[1])].show_all_network()
            self.origin_operator_list = operator_list
            self.show_operator_list()

        elif temp[0] == 'record':
            with open(temp[2], 'w') as f:
                f.write('')
            for i in range(MAX_NODE):
                temp_result = Nodes[i].change_record(temp[1], temp[2])
                print("record switch :", temp_result)

        elif temp[0] == 'route' or temp[0]=='r':
            node=int(temp[1])
            network=temp[3]
            Nodes[node].delete_route(network)
            if self.ifMuti==0:
                self.select_node(network_str_to_tuple(network), node)
                self.origin_operator_list=operator_list
                self.show_operator_list()
                # print("{} 次操作".format(len(operator_list)), operator_list)
                operator_list = []


        elif temp[0] == 'show' or temp[0] == 's':
            if temp[1] == 'network' or temp[1] == 'net':  # 显示能到达的网络
                if temp[2] == 'all':
                    for i in range(MAX_NODE):
                        Nodes[i].show_all_network()
                else:
                    node = int(temp[2])
                    Nodes[node].show_all_network()
            elif temp[1] == "operator" or temp[1] == "o":  # 输出目前为止的操作序列
                self.show_operator_list()
                # print("{} 次操作".format(len(operator_list)), operator_list)

            elif temp[1] == 'config' or temp[1] == 'c':  # 输出配置
                print("algorithm:{}".format(self.type))
                # print("print:{}".format(self.printf))
                if self.printf == 1:
                    print("don't print middle result")
                else:
                    print("print middle result")

            elif temp[1] == 'messages' or temp[1]== 'm':#输出包
                if temp[2]=='all':
                    for i in range(MAX_NODE):
                        show_message_to_node(i)
                else:
                    node=int(temp[2])
                    show_message_to_node(node)

            elif temp[1] =='rule':#输出入站规则
                node=int(temp[2])
                Nodes[node].show_config()



        elif temp[0] == 'shell' or temp[0] == 'sh':
            # 脚本的实现，便于批处理以及代码直接复制
            # temp shell/sh  time(批处理的次数)
            # 最后一行用EOF终止
            self.code = []
            self.fortime = int(temp[1])
            while 1:
                input_data = input("<<")
                if input_data != "EOF":
                    self.code.append(input_data)
                else:
                    break
            for i in range(self.fortime):
                for j in range(len(self.code)):
                    self.deal_input(self.code[j])
            # raise ValueError("need to implement")

        elif temp[0] == 'waiting' or temp[0] == 'wait':
            # 输出目前待处理的节点序列
            select_node_list, node_flag_map = waiting_deal_node_list()
            print("待处理的节点：", select_node_list)

        elif temp[0]=='/muti':
            #muti状态结束了，需要选节点执行了
            self.ifMuti=0
            self.select_node()
            self.origin_operator_list = operator_list
            self.show_operator_list()
            # print("{} 次操作".format(len(operator_list)), operator_list)
            operator_list = []





def read_json_file(path):
    # 读取json格式的文件，但该函数仅支持无向图的json，有向图不支持
    # 其中，node节点的id为名字，它的node id从0开始
    # 由程序自动分配，其中如果有AS属性，则用于记录它的AS号。
    # 而link则通过source和target属性来进行连接
    # e.g.
    # {
    #     ...,
    #     "nodes": [{"id":1,"AS":65000},
    #               {"id":2,"AS":65001}],
    #     "links":[
    #         {"source":1,"target":2}
    #     ]
    # }
    global Nodes
    global G
    global MAX_NODE
    file = open(path, 'r')
    file_content = file.read()
    content = json.loads(file_content)
    nodes = content['nodes']
    links = content['links']
    name_map = {}
    MAX_NODE = len(nodes)
    for index in range(len(nodes)):
        node = nodes[index]
        name_map[node["id"]] = index
        if "AS" in node:
            AS = node["AS"]
        else:
            AS = index
        temp = Node(index, AS, node["id"])
        Nodes.append(temp)
        G.add_node(index)

    for link in links:
        add(name_map[link["source"]], name_map[link["target"]])
        G.add_edge(name_map[link["source"]], name_map[link["target"]])


def run():
    #random.seed(0)#方便复现和调试
    Op = Operator()
    while 1:
        input_data = input("BGP# ")
        Op.deal_input(input_data)


# os.chdir("code")
current_dir = os.getcwd()
# print("当前工作目录：", current_dir)

Nodes = []
draw_times = 0
draw_pos = None
debug=0
G = nx.Graph()
# json_file_path = "topo/graph_clos_4.json"
# json_file_path="topo/topo1.txt"
#json_file_path = "topo/graph_er_40_0.5.json"
#json_file_path="topo/graph_gnm_100_0.3.json"      #对于这张图，代码有bug，出现了节点99、5、12形成圈，但是它们类型为3的情况
#json_file_path="topo/fat_tree_10.json"

json_file_path=input()
read_json_file(json_file_path)

Message_list = []  # message_list是消息队列，记录每个消息
operator_list = []
alltopology={}#它是mytopology的拓展，因为mytopology只是假设有一个net，但多个net时就无法区分了，所以alltopo用来记录多个net，它结构为(net,mytopology)
# mytopology = np.zeros(MAX_NODE, dtype=np.int32)  # 它用来代替greedy里面的topology，然后把它的修改放到node.deal中
mytopo_nodes_type = {}  # 该字典记录了不同network下，每个节点的类型，具体记录为(ip,mask):np ，np记录了节点类型
# mytopo_nodes_best={}#该字典记录了不同network下，每个节点对应的最佳该执行的节点是什么，具体记录为(ip,mask):np ，np记录了节点

plt.ion()
run()
