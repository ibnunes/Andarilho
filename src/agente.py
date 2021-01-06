"""
agente.py

41358, Beatriz Tavares da Costa
41381, Igor Cordeiro Bordalo Nunes
"""

import time

import networkx as nx



OBJ_NURSE   = 'enfermeiro'
OBJ_DOCTOR  = 'medico'
OBJ_PATIENT = 'doente'
OBJ_TABLE   = 'mesa'
OBJ_CHAIR   = 'cadeira'
OBJ_BOOK    = 'livro'
OBJ_BED     = 'cama'

CATEGORY_OBJECT    = [OBJ_TABLE, OBJ_CHAIR, OBJ_BOOK, OBJ_BED]
CATEGORY_PEOPLE    = [OBJ_NURSE, OBJ_DOCTOR, OBJ_PATIENT]
CATEGORY_FURNITURE = [OBJ_BED, OBJ_CHAIR, OBJ_TABLE]
CATEGORY_ALL       = CATEGORY_PEOPLE + CATEGORY_OBJECT

SEPARATOR = '_'

MAP_MIDPOINT = 'mid'
MAP_DISTANCE = 'weight'
MAP_ROBOT    = 'X'

ROOM_UNKNOWN  = 0
ROOM_CORRIDOR = 1
ROOM_BEDROOM  = 2
ROOM_NURSES   = 3
ROOM_WAITING  = 4

ROOM_DESCRIPTION = [
    "Não tenho informação suficiente para determinar",
    "Corredor",
    "Quarto",
    "Sala de enfermeiros",
    "Sala de espera"
]

DIR_STATIC = 0
DIR_RIGHT  = 1
DIR_LEFT   = 2
DIR_UP     = 3
DIR_DOWN   = 4

SIZE_OBJECT = 25
SIZE_WALL   = 15

ERROR_NOT_ENOUGH_PEOPLE = "Não foram encontradas pelo menos 2 pessoas até ao momento"

INIT_POS = (100, 100)


class LinearFunction:
    def __init__(self):
        self._m = 0.0
        self._b = 0.0
        self._p = (0, 0)
        self._q = (0, 0)
        self._defined = False
    
    def setM(self, m):
        self._defined = True
        self._m = m
    
    def setB(self, b):
        self._defined = True
        self._b = b

    def setFrom2Points(self, p, q):
        try:
            m = (p[1] - q[1]) / (p[0] - q[0])
            b = p[1] - m * p[0]
            self._p = p
            self._q = q
            self.setM(m)
            self.setB(b)
        except:
            self._defined = False
    
    def setPointB(self, q):
        self.setFrom2Points(self._p, q)
    
    def getY(self, x):
        return self._m * x + self._b
    
    def getX(self, y):
        if self._m != 0.0:
            return (y - self._b) / self._m
        else:
            return self._b
    
    def getPointA(self):
        return self._p
    
    def getPointB(self):
        return self._q
    
    def isDefined(self):
        return self._defined
    
    def reset(self):
        self._m = 0.0
        self._b = 0.0
        self._defined = False



class Log:
    _flag = True

    @staticmethod
    def d(prompt):
        if Log._flag:
            print("[DEBUG] {0}".format(prompt))
    
    @staticmethod
    def setMode(mode):
        Log._flag = mode != 0



class Things:
    _list_people  = []
    _list_objects = []

    @staticmethod
    def add(category, name):
        if not Things.contains(category, name):
            if category in CATEGORY_PEOPLE:
                Things._list_people.append((category, name))
            else:
                Things._list_objects.append((category, name))
    
    @staticmethod
    def contains(category, name):
        return (category, name) in (Things._list_people + Things._list_objects)
    
    @staticmethod
    def getLastButOnePerson():
        if len(Things._list_people) >= 2:
            return Things._list_people[-2]
        else:
            return ERROR_NOT_ENOUGH_PEOPLE
    
    @staticmethod
    def getListOfPeople():
        return Things._list_people
    
    @staticmethod
    def getListOfObjects():
        return Things._list_objects



class Robot:
    _lastPos = INIT_POS
    _currPos = INIT_POS

    _lastBat = 100.0
    _currBat = 100.0

    _lastTime = time.time()
    _currTime = time.time()
    
    _lastVel = 0.0
    _currVel = 0.0

    _funVB = LinearFunction()   # Velocity vs Battery
    _funBT = LinearFunction()   # Battery vs Time
    _funVT = LinearFunction()   # Velocity vs Time

    @staticmethod
    def getDirection():
        x0, y0 = Robot._lastPos[0], Robot._lastPos[1]
        x1, y1 = Robot._currPos[0], Robot._currPos[1]
        dx, dy = x1 - x0, y1 - y0
        
        if dx == 0 and dy == 0:
            return [DIR_STATIC]
        
        direction = []
        direction.append(DIR_RIGHT if dx > 0 else DIR_LEFT)
        direction.append(DIR_DOWN if dy > 0 else DIR_UP)
        return direction
    

    @staticmethod
    def getAdaptedPosition():
        pos = tuple(Robot._currPos)
        direction = Robot.getDirection()
        if DIR_STATIC in direction:
            return pos
        pos = (pos[0] + SIZE_OBJECT if DIR_RIGHT in direction else -SIZE_OBJECT, pos[1] + SIZE_OBJECT if DIR_DOWN in direction else -SIZE_OBJECT)
        return pos


    @staticmethod
    def updateVelocity():
        if Robot._lastPos != Robot._currPos:
            Robot._currTime, Robot._lastTime = Utils.swap(Robot._currTime, time.time())
            Robot._currVel, Robot._lastVel = Utils.swap(Robot._currVel, Utils.distance(Robot._lastPos, Robot._currPos) / (Robot._currTime - Robot._lastTime))
    
    @staticmethod
    def refreshFunctions():
        if Robot._currBat > Robot._lastBat:
            Robot._funVB.reset()
            Robot._funBT.reset()
            Robot._funVT.reset()
        else:
            if not Robot._funVB.isDefined():
                Robot._funVB.setFrom2Points((Robot._lastBat, Robot._lastVel), (Robot._currBat, Robot._currVel))
            else:
                Robot._funVB.setPointB((Robot._currBat, Robot._currVel))

            if not Robot._funBT.isDefined():
                Robot._funBT.setFrom2Points((Robot._lastTime, Robot._lastBat), (Robot._currTime, Robot._currBat))
            else:
                Robot._funBT.setPointB((Robot._currTime, Robot._currBat))
            
            if not Robot._funVT.isDefined():
                Robot._funVT.setFrom2Points((Robot._lastTime, Robot._lastVel), (Robot._currTime, Robot._currVel))
            else:
                Robot._funVT.setPointB((Robot._currTime, Robot._currVel))

    
    @staticmethod
    def predictTimeFromDistance(distance):
        if Robot._funVT.isDefined():
            vf, vi = Robot._funVT.getPointA()[1], Robot._funVT.getPointB()[1]
            return 2 * distance / (vf + vi)
        else:
            raise Exception("Cannot predict time")
    
    @staticmethod
    def predictTimeFromBattery(battery):
        if Robot._funBT.isDefined():
            return Robot._funBT.getX(battery) - Robot._funBT.getPointA()[0]
        else:
            raise Exception("Cannot predict time")

    @staticmethod
    def setBattery(battery):
        Robot._currBat, Robot._lastBat = Utils.swap(Robot._currBat, battery)

    @staticmethod
    def setPosition(x, y):
        Robot._currPos, Robot._lastPos = Utils.swap(Robot._currPos, (x, y))
    
    @staticmethod
    def updateRobot(position, battery):
        assert len(position) == 2
        Robot.setBattery(battery)
        Robot.setPosition(position[0], position[1])
        Robot.updateVelocity()
        Robot.refreshFunctions()
    
    @staticmethod
    def getPosition():
        return Robot._currPos


class Hospital:
    _rooms = [
        [( 30, 180), ( 30,  90)],   # Escadas
        [( 85, 565), ( 30, 135)],   # Corredor 1
        [( 30,  85), ( 90, 330)],   # Corredor 2
        [(565, 635), ( 30, 330)],   # Corredor 3
        [( 30, 770), (330, 410)],   # Corredor 4
        [(130, 235), (180, 285)],   # Sala 5
        [(280, 385), (180, 285)],   # Sala 6
        [(430, 520), (180, 285)],   # Sala 7
        [(680, 770), ( 30,  85)],   # Sala 8
        [(680, 770), (130, 185)],   # Sala 9
        [(680, 770), (230, 285)],   # Sala 10
        [( 30, 235), (455, 770)],   # Sala 11
        [(280, 385), (455, 770)],   # Sala 12
        [(430, 570), (455, 770)],   # Sala 13
        [(615, 770), (455, 770)],   # Sala 14
    ]

    _lastVisited = 0
    _currentRoom = 0

    _floor = nx.Graph()
    _map = nx.Graph()


    @staticmethod
    def getRoomMidPoint(room):
        return Utils.midpoint(Hospital._rooms[room][0], Hospital._rooms[room][1])


    @staticmethod
    def getFloorGraph():
        return Hospital._floor
    

    @staticmethod
    def getMapGraph():
        return Hospital._map
    

    @staticmethod
    def roomToStr(r):
        return "R{0:02d}".format(r)


    @staticmethod
    def doorToStr(r1, r2):
        return "D{0:02d}{1:02d}".format(min(r1, r2), max(r1, r2))
    

    @staticmethod
    def getEdgeBetweenRoomAndDoor(room_src, room_dest):
        return (Hospital.roomToStr(room_src), Hospital.doorToStr(room_src, room_dest))
    

    @staticmethod
    def getEdgeBetweenDoorAndDoor(r1, r2, r3):
        return (Hospital.doorToStr(r1, r2), Hospital.doorToStr(r1, r3))

    
    @staticmethod
    def computeDirectDoorPaths():
        for r in Hospital._floor.nodes():
            rooms = sorted(list(nx.all_neighbors(Hospital._floor, r)))
            # Log.d("room={0}; neighbors={1}".format(r, rooms))
            for i in range(0, len(rooms)-1):
                for j in range(i+1, len(rooms)):
                    edge = Hospital.getEdgeBetweenDoorAndDoor(r, rooms[i], rooms[j])
                    if not Hospital._map.has_edge(*edge):
                        door_i = Hospital._map.nodes[Hospital.doorToStr(r, rooms[i])][MAP_MIDPOINT]
                        door_j = Hospital._map.nodes[Hospital.doorToStr(r, rooms[j])][MAP_MIDPOINT]
                        distance = Utils.distance(door_i, door_j)
                        Hospital._map.add_edges_from([edge], weight=distance)
    

    @staticmethod
    def updateMap():
        cr, lv, rpos = Hospital._currentRoom, Hospital._lastVisited, Robot.getPosition()

        midpoint = Hospital.getRoomMidPoint(cr)
        distance = Utils.distance(midpoint, rpos)
        Hospital._map.add_edges_from([Hospital.getEdgeBetweenRoomAndDoor(cr, lv)], weight=distance)
        Hospital._map.nodes[Hospital.roomToStr(cr)][MAP_MIDPOINT] = midpoint

        midpoint = Hospital.getRoomMidPoint(lv)
        distance = Utils.distance(midpoint, rpos)
        Hospital._map.add_edges_from([Hospital.getEdgeBetweenRoomAndDoor(lv, cr)], weight=distance)
        Hospital._map.nodes[Hospital.roomToStr(lv)][MAP_MIDPOINT] = midpoint

        Hospital._map.nodes[Hospital.doorToStr(cr, lv)][MAP_MIDPOINT] = rpos
        Hospital.computeDirectDoorPaths()


    @staticmethod
    def updateFloor(newRoom):
        if newRoom != 0:
            if Hospital._currentRoom != newRoom:
                Hospital._currentRoom, Hospital._lastVisited = Utils.swap(Hospital._currentRoom, newRoom)
                Hospital._floor.add_edge(Hospital._currentRoom, Hospital._lastVisited)
                Hospital.updateMap()
                # Log.d("Floor: curr={0}; last={1}".format(Hospital._currentRoom, Hospital._lastVisited))
    

    @staticmethod
    def addRobotToMap():
        Hospital._map.add_node(MAP_ROBOT)
        edges = nx.all_neighbors(Hospital._map, Hospital.roomToStr(Hospital._currentRoom))
        for e in edges:
            distance = Utils.distance(Hospital._map.nodes[e][MAP_MIDPOINT], Robot.getPosition())
            Hospital._map.add_edge(MAP_ROBOT, e, weight=distance)
    

    @staticmethod
    def removeRobotFromMap():
        try:
            Hospital._map.remove_node(MAP_ROBOT)
        except:
            pass


    @staticmethod
    def updateWithPosition(position):
        if len(position) == 0:
            return 0
        else:
            assert len(position) == 2
            px, py = position[0], position[1]
            for i in range(len(Hospital._rooms)):
                rx, ry = Hospital._rooms[i][0], Hospital._rooms[i][1]
                if Utils.inRange(px, rx) and Utils.inRange(py, ry):
                    Hospital.updateFloor(i)
                    return i
            else:
                return 0

    
    @staticmethod
    def updateWithObjects(objects, position):
        if len(objects) > 0:
            position = tuple(position)
            for obj in objects:
                [category, name] = obj.split(SEPARATOR, 1)
                if not Things.contains(category, name):
                    try:
                        currentObjects = list(map(lambda n: n[1], Hospital._floor.nodes[Hospital._currentRoom][category]))
                        if name not in currentObjects:
                            # Hospital._floor.nodes[Hospital._currentRoom][category].append((position, name))
                            Hospital._floor.nodes[Hospital._currentRoom][category].append((Robot.getAdaptedPosition(), name))
                        # Log.d("Current objects of type {0} after append: {1}".format(category, currentObjects))
                    except KeyError:
                        Hospital._floor.nodes[Hospital._currentRoom][category] = [(position, name)]
                        # Log.d("No objects found of type {0}. Added first with name {1}.".format(category, name))
                    Things.add(category, name)


    @staticmethod
    def roomDescription(room_code):
        return ROOM_DESCRIPTION[room_code]


    @staticmethod
    def getTypeOfRoom(room):
        # Quarto: >= 1 cama
        # Sala de enfermeiros: 0 camas, >= 1 cadeiras AND >= 1 mesas
        # Sala de espera: > 2 cadeiras, 0 mesas, 0 camas
        # Corredor: de 1 a 4
        if room in range(1, 5):
            return ROOM_CORRIDOR

        counter = {}
        room_data = Hospital._floor.nodes[room]
        for category in CATEGORY_FURNITURE:
            try:
                counter[category] = len(room_data[category])
            except KeyError:
                counter[category] = 0
        
        if counter[OBJ_BED] >= 1:
            return ROOM_BEDROOM
        elif counter[OBJ_CHAIR] >= 1 and counter[OBJ_TABLE] >= 1:
            return ROOM_NURSES
        elif counter[OBJ_CHAIR] > 2:
            return ROOM_WAITING
        else:
            return ROOM_UNKNOWN
    

    @staticmethod
    def getCurrentTypeOfRoom():
        return Hospital.getTypeOfRoom(Hospital._currentRoom)


    @staticmethod
    def getDistanceToNearestDoctor():
        doctors = []
        for (room, things) in Hospital._floor.nodes(data=True):
            if OBJ_DOCTOR in things:
                doctors += list(map(lambda t: (room, t[0], t[1]), things[OBJ_DOCTOR]))
        if len(doctors) > 0:
            doctors = list(map(lambda d: (d[0], Utils.distance(d[1], Robot.getPosition()), d[2]), doctors))
            doctors.sort(key = lambda d: d[1])
            return "Médico {0} na sala {1} a uma distância de {2:.3f}.".format(doctors[0][2], doctors[0][0], doctors[0][1])
        else:
            return "Ainda não encontrei médicos"
    

    @staticmethod
    def getPathToNearestNurseOffice():
        nurse_rooms = list(filter(lambda n: Hospital.getTypeOfRoom(n) == ROOM_NURSES, Hospital._floor.nodes()))
        result = []
        if len(nurse_rooms) > 0:
            if Hospital.getTypeOfRoom(Hospital._currentRoom) == ROOM_NURSES:
                return [Hospital.roomToStr(Hospital._currentRoom)]
            Hospital.addRobotToMap()
            for r in nurse_rooms:
                try:
                    path   = nx.astar_path(Hospital._map, MAP_ROBOT, Hospital.roomToStr(r))
                    weight = nx.astar_path_length(Hospital._map, MAP_ROBOT, Hospital.roomToStr(r))
                    result.append((weight, path))
                except nx.NetworkXNoPath:
                    continue
            Hospital.removeRobotFromMap()
            if len(result) == 0:
                return []
            result.sort(key = lambda t: t[0])
            return result[0][1]
        else:
            return []
    

    @staticmethod
    def getTimeToStairs():
        Hospital.addRobotToMap()
        # path   = nx.astar_path(Hospital._map, MAP_ROBOT, Hospital.roomToStr(0))
        weight = nx.astar_path_length(Hospital._map, MAP_ROBOT, Hospital.roomToStr(0))
        Hospital.removeRobotFromMap()
        # return (weight, path)
        return Robot.predictTimeFromDistance(weight)
    

    @staticmethod
    def getTimeToDie():
        return Robot.predictTimeFromBattery(0.0)


    @staticmethod
    def getRoomIndex():
        return Hospital._currentRoom



class Utils:
    @staticmethod
    def inRange(n, r):
        assert len(r) == 2
        return n >= r[0] and n <= r[1]
    
    @staticmethod
    def swap(x, y):
        return (y, x)
    
    @staticmethod
    def distance(a, b):
        return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
    
    @staticmethod
    def midpoint(a, b):
        return ((a[0] + a[1]) // 2, (b[0] + b[1]) // 2)
    
    @staticmethod
    def timeToStr(t):
        return "{0:3d} segundos e {1:3d} milissegundos".format(int(t), int((t - int(t)) * 1000))
    
    @staticmethod
    def pathDescription(path):
        desc = ""
        for p in path:
            try:
                if p[0] == 'X':
                    continue
                elif p[0] == 'R':
                    desc += "\nEstá na sala {0:2d}.".format(int(p[1:]))
                elif p[0] == 'D':
                    desc += "\nVá da sala {0:2d} para a sala {1:2d}.".format(int(p[1:3]), int(p[3:]))
                else:
                    raise Exception("I dunno!")
            except:
                desc += "\n[Error: \"{0}\" was not understood by the path descriptor]".format(p)
        return desc if len(desc) > 0 else "Nenhum caminho foi encontrado."


def work(posicao, bateria, objetos):
    # esta função é invocada em cada ciclo de clock
    # e pode servir para armazenar informação recolhida pelo agente
    # recebe:
    # posicao = a posição atual do agente, uma lista [X,Y]
    # bateria = valor de energia na bateria, um número inteiro >= 0
    # objetos = o nome do(s) objeto(s) próximos do agente, uma string

    # podem achar o tempo atual usando, p.ex.
    # time.time()
    # Log.d("Time: {0}".format(time.time()))

    Robot.updateRobot(posicao, bateria)
    Hospital.updateWithPosition(Robot.getPosition())
    Hospital.updateWithObjects(objetos, Robot.getPosition())
    # Log.d("Posicao = [{0}, {1}]; Bateria = {2:.2f}; Objetos = {3}; Sala = {4}".format(pos_x, pos_y, bateria, objetos, Hospital.getRoomIndex()))
    # Log.d("Vm = {0:.3f}; Vl = {1:.3f}; Var = {2 }".format(Robot.getAverageVelocity(), Robot.lastVelocity(), Robot.getVelocityVariance()))


def resp1():
    # Qual foi a penúltima pessoa que viste?
    # Log.d("People: {0}\n Objects: {1}".format(Things.getListOfPeople(), Things.getListOfObjects()))
    # Log.d("Nodes: {0}\nEdges: {1}".format(Hospital.getMapGraph().nodes(data=True), Hospital.getMapGraph().edges(data=True)))
    print("Resposta: {0}".format(Things.getLastButOnePerson()))


def resp2():
    # Em que tipo de sala estás agora?
    # Log.d("Nodes: {0}\nEdges: {1}".format(Hospital.getFloorGraph().nodes(data=True), Hospital.getFloorGraph().edges()))
    print("Resposta: {0}".format(Hospital.roomDescription(Hospital.getCurrentTypeOfRoom())))


def resp3():
    # Qual o caminho para a sala de enfermeiros mais próxima?
    print("Resposta: {0}".format(Utils.pathDescription(Hospital.getPathToNearestNurseOffice())))


def resp4():
    # Qual a distância até ao médico mais próximo?
    print("Resposta: {0}".format(Hospital.getDistanceToNearestDoctor()))


def resp5():
    # Quanto tempo achas que demoras a ir de onde estás até às escadas?
    try:
        print("Resposta: {0}".format(Utils.timeToStr(Hospital.getTimeToStairs())))
    except:
        print("Não tenho dados suficientes para saber como me comporto.")


def resp6():
    # Quanto tempo achas que falta até ficares sem bateria?
    try:
        print("Resposta: {0}".format(Utils.timeToStr(Hospital.getTimeToDie())))
    except: # Exception as e:
        print("Não tenho dados suficientes para saber quando irei entregar a alma ao meu criador.")


def resp7():
    # Qual a probabilidade de encontrar um livro numa divisão se já encontraste uma cadeira?
    print("Pergunta 7")
    pass


def resp8():
    # Se encontrares um enfermeiro numa divisão, qual é a probabilidade de estar lá um doente?
    print("Pergunta 8")
    pass
