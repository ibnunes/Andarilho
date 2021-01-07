# -*- coding: utf-8 -*-

"""
agente.py

41358, Beatriz Tavares da Costa
41381, Igor Cordeiro Bordalo Nunes
"""

import time

# A biblioteca networkx fornece métodos para trabalhar com grafos
import networkx as nx

import matplotlib.pyplot as plt


# -----------------------------------------------------------------------------
# CONSTANTES
# -----------------------------------------------------------------------------

# OBJ_*: Permite identificar os objetos ou pessoas encontrados conforme a nomenclatura fornecida pelo robot
OBJ_NURSE   = 'enfermeiro'
OBJ_DOCTOR  = 'medico'
OBJ_PATIENT = 'doente'
OBJ_TABLE   = 'mesa'
OBJ_CHAIR   = 'cadeira'
OBJ_BOOK    = 'livro'
OBJ_BED     = 'cama'


#CATEGORY_*: Aglutina objetos em categorias para fácil identificação nos algoritmos correspondentes
CATEGORY_OBJECT    = [OBJ_TABLE, OBJ_CHAIR, OBJ_BOOK, OBJ_BED]      # Objetos
CATEGORY_PEOPLE    = [OBJ_NURSE, OBJ_DOCTOR, OBJ_PATIENT]           # Pessoas
CATEGORY_FURNITURE = [OBJ_BED, OBJ_CHAIR, OBJ_TABLE]                # Mobília
CATEGORY_ALL       = CATEGORY_PEOPLE + CATEGORY_OBJECT              # Todos


# O separador utilizado pelo robot para distinguir a categoria do nome do objeto
SEPARATOR = '_'


# MAP_*: nomes para o grafo do mapa
MAP_MIDPOINT = 'mid'        # Atributo: ponto médio de uma divisão
MAP_DISTANCE = 'weight'     # Atributo: distância entre dois nodos
MAP_ROBOT    = 'X'          # Objecto: robot


# ROOM_*: Codifica cada tipo de sala com um inteiro e descreve-os
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

# DIR_*: Codifica cada direção do robot com um inteiro
DIR_STATIC = 0
DIR_RIGHT  = 1
DIR_LEFT   = 2
DIR_UP     = 3
DIR_DOWN   = 4

# SIZE_*: Tamanho de cada tipo de objecto que compõe o mundo
SIZE_OBJECT = 25
SIZE_WALL   = 15

# Mensagem padrão para quando não são encontradas pelo menos 2 pessoas
ERROR_NOT_ENOUGH_PEOPLE = "Não foram encontradas pelo menos 2 pessoas até ao momento"

# Posição inicial do robot segundo o enunciado
INIT_POS = (100, 100)


# -----------------------------------------------------------------------------
# CLASSES
# -----------------------------------------------------------------------------

class LinearFunction:
    """Esta classe gere uma função linear do tipo y=mx+b."""

    def __init__(self):
        self._m = 0.0           # Declive
        self._b = 0.0           # Intersecção com o eixo YY
        self._p = (0, 0)        # Ponto A: primeiro ponto da reta
        self._q = (0, 0)        # Ponto B: segundo ponto da reta
        self._defined = False   # Flag que indica se a função está definida

    def setFrom2Points(self, p, q):
        """Define a função dados dois pontos"""
        try:
            m = (p[1] - q[1]) / (p[0] - q[0])
            b = p[1] - m * p[0]
            self._p = tuple(p)
            self._q = tuple(q)
            self._m = m
            self._b = b
            self._defined = True
        except:
            self._defined = False
    
    def setPointB(self, q):
        """Redefine a função mudando o ponto B e mantendo o ponto A"""
        self.setFrom2Points(self._p, q)
    
    def getY(self, x):
        """Dado um valor X, devolve o Y correspondente"""
        return self._m * x + self._b
    
    def getX(self, y):
        """Dado um valor Y, devolve o X correspondente"""
        if self._m != 0.0:
            return (y - self._b) / self._m
        else:
            return self._b
    
    def getPointA(self):
        """Retorna o ponto A da reta"""
        return self._p
    
    def getPointB(self):
        """Retorna o ponto B da reta"""
        return self._q
    
    def isDefined(self):
        """Indica se a função está corretamente definida"""
        return self._defined
    
    def reset(self):
        """Reinicia a instância ao estado inicial"""
        self._m = 0.0
        self._b = 0.0
        self._p = (0, 0)
        self._q = (0, 0)
        self._defined = False



class Log:
    """Classe para auxiliar o debugging do código.
    Todos os seus usos foram eliminados ou comentados na versão final."""

    _flag = True    # Flag que indica se deve fazer output ou se deve ignorar

    @staticmethod
    def d(prompt):
        """Output de debug"""
        if Log._flag:
            print("[DEBUG] {0}".format(prompt))
    
    @staticmethod
    def setMode(mode):
        """Define o modo através de um booleano"""
        Log._flag = mode



class Things:
    """Classe que guarda em memória as pessoas e os objetos que o robot encontrou sem os repetir.
    Guarda de igual forma a penúltima pessoa encontrada."""

    _list_people     = []
    _list_objects    = []
    _two_last_people = ("", "")     # [Current, Last]
    _last_was_blank  = True

    @staticmethod
    def add(category, name):
        """Adiciona a categoria e o nome do objeto se for novo.
        Atualiza, se necessário e se for o caso, o tuplo das duas últimas pessoas encontradas."""
        if not Things.contains(category, name):
            if category in CATEGORY_PEOPLE:
                Things._list_people.append((category, name))
            else:
                Things._list_objects.append((category, name))
        if category in CATEGORY_PEOPLE and Things._last_was_blank:
            Things._two_last_people = Utils.swap(Things._two_last_people[0], name)
    
    @staticmethod
    def contains(category, name):
        """Verifica se um dado par (categoria, nome) já foi encontrado."""
        return (category, name) in (Things._list_people + Things._list_objects)
    
    @staticmethod
    def setWasBlank(blank):
        """Define se o robot não encontrou nada na última atualização de estado."""
        Things._last_was_blank = blank
    
    @staticmethod
    def getLastButOnePerson():
        """[PERGUNTA 1]
        Obtém a penúltima pessoa vista, se disponível."""
        if Things._two_last_people[1] != "":
            return Things._two_last_people[1]
        else:
            return ERROR_NOT_ENOUGH_PEOPLE
    
    @staticmethod
    def getListOfPeople():
        return Things._list_people
    
    @staticmethod
    def getListOfObjects():
        return Things._list_objects



class Robot:
    """Classe para gerir os recursos do robot e estimar os gastos de bateria e a velocidade a cada momento."""

    # Posição: anterior e atual
    _lastPos = INIT_POS
    _currPos = INIT_POS

    # Bateria: anterior e atual
    _lastBat = 100.0
    _currBat = 100.0

    # Tempo (relógio): anterior e atual
    _lastTime = time.time()
    _currTime = time.time()
    
    # Velocidade: anterior e atual
    _lastVel = 0.0
    _currVel = 0.0

    _funVB = LinearFunction()   # Velocity vs. Battery
    _funBT = LinearFunction()   # Battery  vs. Time
    _funVT = LinearFunction()   # Velocity vs. Time

    @staticmethod
    def getDirection():
        """Determina a direção do robot tendo em conta a posição atual e a anterior.
        Devolve uma lista de 1 a 2 elementos que permite estimar 8 direções ou se está parado."""

        x0, y0 = Robot._lastPos[0], Robot._lastPos[1]
        x1, y1 = Robot._currPos[0], Robot._currPos[1]
        dx, dy = x1 - x0, y1 - y0
        
        if dx == 0 and dy == 0:
            return [DIR_STATIC]
        
        direction = []
        if dx != 0:
            direction.append(DIR_RIGHT if dx > 0 else DIR_LEFT)
        if dy != 0:
            direction.append(DIR_DOWN if dy > 0 else DIR_UP)
        return direction
    

    @staticmethod
    def getAdaptedPosition():
        """Devolve a posição adaptada de um objeto encontrado tendo em conta a posição atual e a direção do robot."""
        pos = tuple(Robot._currPos)
        direction = Robot.getDirection()
        if DIR_STATIC in direction:
            return pos
        pos = (pos[0] + SIZE_OBJECT if DIR_RIGHT in direction else -SIZE_OBJECT, pos[1] + SIZE_OBJECT if DIR_DOWN in direction else -SIZE_OBJECT)
        return pos


    @staticmethod
    def updateVelocity():
        """Atualiza a velocidade caso o robot se tenha movido"""
        if Robot._lastPos != Robot._currPos:
            Robot._currTime, Robot._lastTime = Utils.swap(Robot._currTime, time.time())
            Robot._currVel, Robot._lastVel = Utils.swap(Robot._currVel, Utils.distance(Robot._lastPos, Robot._currPos) / (Robot._currTime - Robot._lastTime))
    

    @staticmethod
    def refreshFunctions():
        """Atualiza as funções lineares que permitem estimar os parâmetros bateria, velocidade e tempo."""

        # Se o robot foi carregado, as funções são reiniciadas
        if Robot._currBat > Robot._lastBat:
            Robot._funVB.reset()
            Robot._funBT.reset()
            Robot._funVT.reset()
        else:
            # Caso as funções estejam definidas, é apenas atualizado o ponto B
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
        """Estima quanto tempo deverá demorar a percorrer uma dada distância.
        Não verifica a validade da distância!"""

        if Robot._funVT.isDefined():
            vf, vi = Robot._funVT.getPointA()[1], Robot._funVT.getPointB()[1]
            return 2 * distance / (vf + vi)

            # Algoritmo:
            # v = d/t, portanto t = d/v.
            # Contudo, a velocidade inicial e final são diferentes, pelo que podemos representar o problema como um trapézio:
            # 
            #       <---vf-->
            # 
            #       +-------+     ^
            #      /         \    |
            #     /     d     \   Δt
            #    /             \  |
            #    +-------------+  V
            # 
            #    <------vi----->
            # 
            # Tal deve-se ao facto de a função utilizada ser linear.
            # Ora, se a distância é a área sob a curva da função v(t), e a "curva" é um segmento de reta, ficamos com um trapézio.
            # Por matemática clássica, temos que:
            #   d = (vf + vi) / 2 * Δt
            # Portanto:
            #   Δt = (2 * d) / (vf + vi)

        else:
            raise Exception("Cannot predict time")
    

    @staticmethod
    def predictTimeFromBattery(battery):
        """Estima quanto tempo deverá demorar até atingir um certo nível de bateria.
        O valor é fornecido em percentagem (de 0.0 a 100.0).
        Não verifica a valodade do valor da bateria!"""

        if Robot._funBT.isDefined():
            return Robot._funBT.getX(battery) - Robot._funBT.getPointB()[0]
        else:
            raise Exception("Cannot predict time")


    @staticmethod
    def setBattery(battery):
        """Atualiza o estado da bateria (em percentagem)."""
        Robot._currBat, Robot._lastBat = Utils.swap(Robot._currBat, battery)


    @staticmethod
    def setPosition(x, y):
        """Atualiza a posição atual do robot."""
        Robot._currPos, Robot._lastPos = Utils.swap(Robot._currPos, (x, y))
    

    @staticmethod
    def updateRobot(position, battery):
        """Atualiza o estado completo do robot tendo em conta a posição atual e a bateria restante."""
        assert len(position) == 2
        Robot.setBattery(battery)
        Robot.setPosition(position[0], position[1])
        Robot.updateVelocity()
        Robot.refreshFunctions()
    
    @staticmethod
    def getPosition():
        """Devolve a posição atual do robot."""
        return Robot._currPos



class Hospital:
    """Principal classe do programa na qual a informação relativa ao piso do hospital é atualizada conforme as informações dadas pelo robot."""

    # Coordenadas das salas e corredores do piso
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

    _lastVisited = 0        # Última sala visitada
    _currentRoom = 0        # Sala onde o robot se encontra atualmente

    # Grafo "floor":
    # Grafo para as ligações entres as salas (permite determinar as conexões entre salas por portas).
    # Cada nodo armazena um dicionário com os objetos encontrados, onde as categorias são as keys do dicionário.
    # Permite determinar qual o tipo de cada sala e quais os objetos em si presentes.
    _floor = nx.Graph()

    # Grafo "map":
    # Grafo para representar os pontos médios das salas e a localização das portas.
    # Cada nodo armazena a posição (x, y) e cada aresta armazena a distância entre os nodos.
    # Permite determinar os caminhos mais curtos entre salas e, com o auxílio da classe Robot, estimar o tempo para chegar até uma sala.
    _map = nx.Graph()


    @staticmethod
    def getRoomMidPoint(room):
        """Calcula o ponto médio de uma divisão do piso."""
        return Utils.midpoint(Hospital._rooms[room][0], Hospital._rooms[room][1])


    @staticmethod
    def getFloorGraph():
        return Hospital._floor
    

    @staticmethod
    def getMapGraph():
        return Hospital._map
    

    @staticmethod
    def roomToStr(r):
        """Codifica uma sala no formato RXX, onde XX é o número da sala."""
        return "R{0:02d}".format(r)


    @staticmethod
    def doorToStr(r1, r2):
        """Codifica uma porta no formato DXXYY, onde XX e YY são os números das salas que a porta conecta."""
        return "D{0:02d}{1:02d}".format(min(r1, r2), max(r1, r2))
    

    @staticmethod
    def getEdgeBetweenRoomAndDoor(room_src, room_dest):
        """Cria um tuplo que representa uma aresta entre duas salas.
        É feita a codificação em string para o grafo map com recurso ao método roomToStr()."""
        return (Hospital.roomToStr(room_src), Hospital.doorToStr(room_src, room_dest))
    

    @staticmethod
    def getEdgeBetweenDoorAndDoor(r1, r2, r3):
        """Cria um tuplo que representa uma aresta entre duas portas.
        São fornecidas as 3 salas pela ordem (sala do meio, sala da esquerda, sala da direita).
        É feita a codificação em string para o grafo map com recurso ao método doorToStr()."""
        return (Hospital.doorToStr(r1, r2), Hospital.doorToStr(r1, r3))

    
    @staticmethod
    def computeDirectDoorPaths():
        """Atualiza o grafo map com ligações diretas entre portas que permitam reduzir o caminho do robot.
        Tal permite evitar que o caminho estimado considere sempre o ponto médio das salas, o que eventualmente
        poderia gerar resultados indesejáveis nos algoritmos de path finding."""

        # Algoritmo:
        # Para cada nodo do grafo floor são considerados os seus vizinhos.
        # Entre cada par de vizinhos é criada uma aresta, caso não exista, no grafo map entre as respetivas portas.

        for r in Hospital._floor.nodes():
            rooms = sorted(list(nx.all_neighbors(Hospital._floor, r)))
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
        """Atualiza o grafo map com os novos dados anteriormente obtidos."""

        cr, lv, rpos = Hospital._currentRoom, Hospital._lastVisited, Robot.getPosition()

        # Faz a ligação entre a sala atual e a porta com a sala anterior
        midpoint = Hospital.getRoomMidPoint(cr)
        distance = Utils.distance(midpoint, rpos)
        Hospital._map.add_edges_from([Hospital.getEdgeBetweenRoomAndDoor(cr, lv)], weight=distance)
        Hospital._map.nodes[Hospital.roomToStr(cr)][MAP_MIDPOINT] = midpoint

        # Faz a ligação entre a sala anterior e a porta com a sala corrente
        midpoint = Hospital.getRoomMidPoint(lv)
        distance = Utils.distance(midpoint, rpos)
        Hospital._map.add_edges_from([Hospital.getEdgeBetweenRoomAndDoor(lv, cr)], weight=distance)
        Hospital._map.nodes[Hospital.roomToStr(lv)][MAP_MIDPOINT] = midpoint

        # Indica a posição da porta:
        Hospital._map.nodes[Hospital.doorToStr(cr, lv)][MAP_MIDPOINT] = rpos

        # Resultado:   (Sala CR) ------------ [Porta CR/LV] ------------ (Sala LV)

        # Atualiza o grafo map com ligações diretas entre portas
        Hospital.computeDirectDoorPaths()


    @staticmethod
    def updateFloor(newRoom):
        """Atualiza, se necessário, o grafo floor com uma nova sala.
        Em caso de atualização, é feita automaticamente a atualização do grafo map."""

        if newRoom != 0:
            if Hospital._currentRoom != newRoom:
                Hospital._currentRoom, Hospital._lastVisited = Utils.swap(Hospital._currentRoom, newRoom)
                Hospital._floor.add_edge(Hospital._currentRoom, Hospital._lastVisited)
                Hospital.updateMap()
    

    @staticmethod
    def addRobotToMap():
        """Adiciona o robot ao grafo map na sua posição atual.
        Essencial para estimar corretamente os caminhos mais curtos com algoritmos de path finding.
        Faz a ligação entre o robot e todos os vizinhos da sala atual no grafo map."""

        Hospital._map.add_node(MAP_ROBOT)
        edges = nx.all_neighbors(Hospital._map, Hospital.roomToStr(Hospital._currentRoom))
        for e in edges:
            distance = Utils.distance(Hospital._map.nodes[e][MAP_MIDPOINT], Robot.getPosition())
            Hospital._map.add_edge(MAP_ROBOT, e, weight=distance)
    

    @staticmethod
    def removeRobotFromMap():
        """Remove o robot do grafo map.
        Esta função deve ser invocada assim que o robot deixe de ser necessário para path finding."""
        try:
            Hospital._map.remove_node(MAP_ROBOT)
        except:
            pass


    @staticmethod
    def updateWithPosition(position):
        """Atualiza o grafo floor (e, por conseguinte, o grafo map) com a sala atual.
        Tal só será de facto efetivado caso a sala seja diferente da anterior."""

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
        """Atualiza o grafo floor com os objetos encontrados na sala e posição atuais.
        Irá de igual forma informar a classe Things destes objetos."""

        # Para cada objeto encontrado são obtidos a sua categoria e o seu nome.
        # Caso a classe Things não contenha este par, então o objeto é adicionado ao grafo floor.
        # A classe Things é igualmente atualizada para poder determinar se é uma pessoa e assim atualizar a penúltima pessoa encontrada.

        if len(objects) > 0:
            position = tuple(position)
            for obj in objects:
                [category, name] = obj.split(SEPARATOR, 1)
                if not Things.contains(category, name):
                    try:
                        currentObjects = list(map(lambda n: n[1], Hospital._floor.nodes[Hospital._currentRoom][category]))
                        if name not in currentObjects:
                            Hospital._floor.nodes[Hospital._currentRoom][category].append((Robot.getAdaptedPosition(), name))
                    except KeyError:
                        Hospital._floor.nodes[Hospital._currentRoom][category] = [(position, name)]
                Things.add(category, name)
            Things.setWasBlank(False)   # Foram encontrados objetos ou pessoas
        else:
            Things.setWasBlank(True)    # Não há objetos encontrados


    @staticmethod
    def roomDescription(room_code):
        """Devolve a descrição de uma sala dado o seu número."""
        return ROOM_DESCRIPTION[room_code]


    @staticmethod
    def getTypeOfRoom(room):
        """Determina qual o tipo de sala dado o seu número.
        Devolve um inteiro que codifica a informação.
        A sua descrição pode ser obtida com o método roomDescription()."""

        # Quarto:               >= 1 cama
        # Sala de enfermeiros:  0 camas, >= 1 cadeiras AND >= 1 mesas
        # Sala de espera:       > 2 cadeiras, 0 mesas, 0 camas
        # Corredor:             índices de 1 a 4
        # Escadas:              índice 0

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
        """Permite determinar o tipo da sala onde o robot se encontra atualmente."""
        return Hospital.getTypeOfRoom(Hospital._currentRoom)


    @staticmethod
    def getDistanceToNearestDoctor():
        """Determina a distância até ao médico mais próximo, que seja do conhecimento do robot."""

        # NOTA: Utiliza a distância euclidiana uma vez que não é pedido o caminho.
        # 1. Encontra todos os médicos em todas as salas visitadas até ao momento e codifica-os em 3-tuplos (sala, posição, nome).
        # 2. Mapeia os 3-tuplos de forma a transformar a posição em distâncias euclidianas.
        # 3. Ordena a lista pela distância.
        # 4. Devolve a informação detalhada sobre o médico (nome, sala onde se encontra e distância em linha reta).

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
        """Determina o caminho mais curto até à sala de enfermeiros mais próxima.
        Recorre ao algoritmo A* sobre o grafo map."""

        # Determina quais as salas de enfermeiros encontradas até ao momento
        nurse_rooms = list(filter(lambda n: Hospital.getTypeOfRoom(n) == ROOM_NURSES, Hospital._floor.nodes()))

        # Se houver salas de enfermeiros, determina o caminho mais curto até cada uma delas e a respetiva distância.
        # A lista resultante, contendo tuplos (distância, caminho), é ordenada pela distância.
        # O caminho do primeiro elemento da lista ordenada é então retornado.
        # O robot é adicionado temporariamente ao grafo map para obter um resultado mais exato.

        if len(nurse_rooms) > 0:
            result = []
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
        """Determina o tempo estimado até chegar às escadas a partir da posição atual do robot.
        Recorre ao algoritmo A* sobre o grafo map."""

        # O robot é adicionado temporariamente ao grafo map para obter um resultado mais exato.
        Hospital.addRobotToMap()
        weight = nx.astar_path_length(Hospital._map, MAP_ROBOT, Hospital.roomToStr(0))
        Hospital.removeRobotFromMap()
        return Robot.predictTimeFromDistance(weight)
    

    @staticmethod
    def getProbabilityOfPatientKnowingNurses():
        """Determina a probabilidade de encontrar um doente sabendo que encontrou um enfermeiro."""

        # Contabiliza as salas encontradas que não são corredores nem escadas,
        # assim como as salas com enfermeiros e as salas com enfermeiros e doentes.
        total_rooms                    = 0
        rooms_with_nurses              = 0
        rooms_with_nurses_and_patients = 0

        for (room, things) in Hospital._floor.nodes(data=True):
            if room not in range(0, 5):
                total_rooms += 1
            if OBJ_NURSE in things:
                rooms_with_nurses += 1
                if OBJ_PATIENT in things:
                    rooms_with_nurses_and_patients += 1

        # Probabilidade de existir doente e enfermeiros numa divisão
        prob_patient_and_nurse = rooms_with_nurses_and_patients / total_rooms

        # Probabilidade de existir enfermeiros na divisão
        prob_nurse = rooms_with_nurses / total_rooms
        
        # Probabilidade condicionada
        return prob_patient_and_nurse / prob_nurse
    

    @staticmethod
    def getProbabilityOfBookIfChairFound():
        """Determina a probabilidade de encontrar um livro caso encontre uma cadeira."""

        # Contabiliza as salas encontradas que não são corredores nem escadas
        total_rooms = 0
        
        # Contabiliza as restantes salas necessárias ao cálculo da probabilidade

        # Let:
        #   L = Book
        #   C = Chair
        #   X = Bed
        #   n = NOT
        # Example: LCnX = Book and Chair and NOT Bed

        rooms_C     = 0     # Salas com cadeiras
        rooms_X     = 0     # Salas com camas
        rooms_CX    = 0     # Salas com cadeiras e camas
        rooms_LCX   = 0     # Salas com livros, cadeiras e camas
        rooms_LCnX  = 0     # Salas com livros e cadeiras, mas sem camas

        for (room, things) in Hospital._floor.nodes(data=True):
            if room not in range(0, 5):
                total_rooms += 1
            
            if OBJ_CHAIR in things:
                rooms_C += 1
            if OBJ_BED in things:
                rooms_X += 1
            
            if set([OBJ_CHAIR, OBJ_BED]).issubset(set(things)):
                rooms_CX += 1
            if set([OBJ_BOOK, OBJ_CHAIR, OBJ_BED]).issubset(set(things)):
                rooms_LCX += 1
            elif set([OBJ_BOOK, OBJ_CHAIR]).issubset(set(things)):
                rooms_LCnX += 1

        # Cálculo das probabilidades
        prob_X = rooms_X / total_rooms
        prob_C = rooms_C / total_rooms
        prob_L_knowing_CX = [rooms_LCX / rooms_CX, rooms_LCnX / rooms_CX]

        # Somatório das probabilidades
        prob_sum  = (1 - prob_X) * prob_C * prob_L_knowing_CX[0]
        prob_sum += prob_X * prob_C * prob_L_knowing_CX[1]

        # Probabilidade condicionada baseada numa Rede Bayesiana
        return prob_sum / prob_C


    @staticmethod
    def getTimeToDie():
        """Estima o tempo restante da bateria até esta esgotar."""
        return Robot.predictTimeFromBattery(0.0)


    @staticmethod
    def getRoomIndex():
        """Devolve a sala atual"""
        return Hospital._currentRoom



class Utils:
    """Classe com funções úteis e auxiliares ao programa."""

    @staticmethod
    def inRange(n, r):
        """Determina se um número se encontra num determinado range"""
        assert len(r) == 2
        return n >= r[0] and n <= r[1]
    

    @staticmethod
    def swap(x, y):
        """Troca os valores x e y num tuplo (y, x)."""
        # Evita o uso de variáveis temporárias
        return (y, x)
    

    @staticmethod
    def distance(a, b):
        """Determina a distância entre dois pontos."""
        return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
    

    @staticmethod
    def midpoint(a, b):
        """Determina o ponto médio de uma área retangular dados dois pontos opostos."""
        return ((a[0] + a[1]) // 2, (b[0] + b[1]) // 2)
    

    @staticmethod
    def timeToStr(t):
        """Formata um dado tempo em segundos e milissegundos."""
        return "{0:3d} segundos e {1:3d} milissegundos".format(int(t), int((t - int(t)) * 1000))
    

    @staticmethod
    def pathDescription(path):
        """Formata um caminho em frases legíveis para humanos.
        Tem em consideração a formatação utilizada pelo grafo map da classe Hospital."""

        desc = ""
        for p in path:
            try:
                if p[0] == 'X':     # Robot, é sempre o primeiro elemento
                    continue
                elif p[0] == 'R':   # Sala
                    desc += "\nEstá na sala {0:2d}.".format(int(p[1:]))
                elif p[0] == 'D':   # Porta -> indica um caminho a fazer entre duas salas
                    desc += "\nVá da sala {0:2d} para a sala {1:2d}.".format(int(p[1:3]), int(p[3:]))
                else:
                    raise Exception("I dunno!")     # Outros formatos desconhecidos, interrompe a execução
            except:
                desc += "\n[Error: \"{0}\" was not understood by the path descriptor]".format(p)
        return desc if len(desc) > 0 else "Nenhum caminho foi encontrado."




# -----------------------------------------------------------------------------
# FUNÇÃO DE TRABALHO
# -----------------------------------------------------------------------------

def work(posicao, bateria, objetos):
    """Esta função é invocada em cada ciclo de clock.
    Recebe:
    posicao -> a posição atual do agente, uma lista [X,Y]
    bateria -> valor de energia na bateria, um número inteiro >= 0
    objetos -> o nome do(s) objeto(s) próximos do agente, uma string"""

    # Dada a estrutura do código, esta função apenas tem de fazer 3 coisas:
    # 1. Atualizar a posição do robot na classe Robot;
    # 2. Atualizar a classe Hospital com a nova posição do Robot;
    # 3. Informar quais os objetos encontrados pelo robot.
    # Todo o processamento associado a estas informações é feito automaticamente pelas classes.

    Robot.updateRobot(posicao, bateria)
    Hospital.updateWithPosition(Robot.getPosition())
    Hospital.updateWithObjects(objetos, Robot.getPosition())



# -----------------------------------------------------------------------------
# RESPOSTAS ÀS PERGUNTAS
# -----------------------------------------------------------------------------

# As respostas são fornecidas por métodos previamente implementados nas respetivas classes.
# É apenas necessário obter o resultado destas funções e formatar o output quando necessário.
# O tratamento de algumas exceções é feito nestas funções a fim de obter informações sobre
# os erros encontrados e porventura adaptar a mensagem consoante o tipo de erro.


def resp1():
    # Qual foi a penúltima pessoa que viste?
    print("Resposta: {0}\n".format(Things.getLastButOnePerson()))
    # nx.draw(Hospital._floor, with_labels=True)
    # plt.savefig("floor.png")
    # plt.clf()
    # nx.draw(Hospital._map, with_labels=True)
    # plt.savefig("map.png")
    # plt.clf()
    nx.draw_random(Hospital._map, with_labels=True)
    plt.savefig("map2.png")
    plt.clf()
    nx.draw_circular(Hospital._map, with_labels=True)
    plt.savefig("map3.png")
    plt.clf()
    nx.draw_spectral(Hospital._map, with_labels=True)
    plt.savefig("map4.png")
    plt.clf()
    nx.draw_spring(Hospital._map, with_labels=True)
    plt.savefig("map5.png")


def resp2():
    # Em que tipo de sala estás agora?
    print("Resposta: {0}\n".format(Hospital.roomDescription(Hospital.getCurrentTypeOfRoom())))


def resp3():
    # Qual o caminho para a sala de enfermeiros mais próxima?
    print("Resposta: {0}\n".format(Utils.pathDescription(Hospital.getPathToNearestNurseOffice())))


def resp4():
    # Qual a distância até ao médico mais próximo?
    print("Resposta: {0}\n".format(Hospital.getDistanceToNearestDoctor()))


def resp5():
    # Quanto tempo achas que demoras a ir de onde estás até às escadas?
    try:
        print("Resposta: {0}\n".format(Utils.timeToStr(Hospital.getTimeToStairs())))
    except:
        print("Não tenho dados suficientes para saber como me comporto.\n")


def resp6():
    # Quanto tempo achas que falta até ficares sem bateria?
    try:
        print("Resposta: {0}\n".format(Utils.timeToStr(Hospital.getTimeToDie())))
    except:
        print("Não tenho dados suficientes para saber quando irei entregar a alma ao meu criador.\n")


def resp7():
    # Qual a probabilidade de encontrar um livro numa divisão se já encontraste uma cadeira?
    try:
        print("Resposta: {0:.3f}\n".format(Hospital.getProbabilityOfBookIfChairFound()))
    except ZeroDivisionError:
        print("Não me é possível calcular esta probabilidade de momento (divisão por zero)\n")
    except Exception as e:
        print("Ocorreu um erro não previsto: {0}\n".format(repr(e)))


def resp8():
    # Se encontrares um enfermeiro numa divisão, qual é a probabilidade de estar lá um doente?
    try:
        print("Resposta: {0:.3f}\n".format(Hospital.getProbabilityOfPatientKnowingNurses()))
    except ZeroDivisionError:
        print("Não me é possível calcular esta probabilidade de momento (divisão por zero)\n")
    except Exception as e:
        print("Ocorreu um erro não previsto: {0}\n".format(repr(e)))
