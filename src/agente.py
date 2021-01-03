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

SEPARATOR   = '_'


ERROR_NOT_ENOUGH_PEOPLE = "Não foram encontradas pelo menos 2 pessoas até ao momento"



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

    @staticmethod
    def getFloorGraph():
        return Hospital._floor

    @staticmethod
    def updateFloor(newRoom):
        if newRoom != 0:
            if Hospital._currentRoom != newRoom:
                Hospital._currentRoom, Hospital._lastVisited = Utils.swap(Hospital._currentRoom, newRoom)
                Hospital._floor.add_edge(Hospital._currentRoom, Hospital._lastVisited)
                Log.d("curr: {0}; last: {1}".format(Hospital._currentRoom, Hospital._lastVisited))

    @staticmethod
    def updateWithPosition(position):
        if position == []:
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
        if objects != []:
            position = tuple(position)
            for obj in objects:
                [category, name] = obj.split(SEPARATOR, 1)
                if not Things.contains(category, name):
                    try:
                        currentObjects = list(map(lambda n: n[1], Hospital._floor.nodes[Hospital._currentRoom][category]))
                        if name not in currentObjects:
                            Hospital._floor.nodes[Hospital._currentRoom][category].append((position, name))
                        # Log.d("Current objects of type {0} after append: {1}".format(category, currentObjects))
                    except KeyError:
                        Hospital._floor.nodes[Hospital._currentRoom][category] = [(position, name)]
                        # Log.d("No objects found of type {0}. Added first with name {1}.".format(category, name))
                    Things.add(category, name)
    
    @staticmethod
    def getTypeOfRoom():
        # Quarto: >= 1 cama
        # Sala de enfermeiros: 0 camas, >= 1 cadeiras AND >= 1 mesas
        # Sala de espera: > 2 cadeiras, 0 mesas, 0 camas
        # Corredor: de 1 a 4
        if Hospital._currentRoom in range(1, 5):
            return "Corredor"

        counter = {}
        room = Hospital._floor.nodes[Hospital._currentRoom]
        for category in CATEGORY_FURNITURE:
            try:
                counter[category] = len(room[category])
            except KeyError:
                counter[category] = 0
        
        if counter[OBJ_BED] >= 1:
            return "Quarto"
        elif counter[OBJ_CHAIR] >= 1 and counter[OBJ_TABLE] >= 1:
            return "Sala de enfermeiros"
        elif counter[OBJ_CHAIR] > 2:
            return "Sala de espera"
        else:
            return "Não tenho informação suficiente para determinar"



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



def work(posicao, bateria, objetos):
    # esta função é invocada em cada ciclo de clock
    # e pode servir para armazenar informação recolhida pelo agente
    # recebe:
    # posicao = a posição atual do agente, uma lista [X,Y]
    # bateria = valor de energia na bateria, um número inteiro >= 0
    # objetos = o nome do(s) objeto(s) próximos do agente, uma string

    # podem achar o tempo atual usando, p.ex.
    # time.time()

    global pos_x
    global pos_y
    
    #copia as posicoes para o posicao1 para podermos utilizar nas questoes
    #posicao1.extend(posicao)
    pos_x = posicao[0]
    pos_y = posicao[1]

    Hospital.updateWithPosition(posicao)
    Hospital.updateWithObjects(objetos, posicao)
    # Log.d("Posicao = [{0}, {1}]; Bateria = {2:.2f}; Objetos = {3}; Sala = {4}".format(pos_x, pos_y, bateria, objetos, Hospital.getRoomIndex()))
    


def resp1():
    # Qual foi a penúltima pessoa que viste?
    # Log.d("People: {0}\n Objects: {1}".format(Things.getListOfPeople(), Things.getListOfObjects()))
    print("Resposta: {0}".format(Things.getLastButOnePerson()))


def resp2():
    # Em que tipo de sala estás agora?
    # Log.d("Nodes: {0}\nEdges: {1}".format(Hospital.getFloorGraph().nodes(data=True), Hospital.getFloorGraph().edges()))
    print("Resposta: {0}".format(Hospital.getTypeOfRoom()))


def resp3():
    # Qual o caminho para a sala de enfermeiros mais próxima?
    print("Pergunta 3")
    pass


def resp4():
    # Qual a distância até ao médico mais próximo?
    print("Pergunta 4")
    pass


def resp5():
    # Quanto tempo achas que demoras a ir de onde estás até às escadas?
    print("Pergunta 5")
    pass


def resp6():
    # Quanto tempo achas que falta até ficares sem bateria?
    print("Pergunta 6")
    pass


def resp7():
    # Qual a probabilidade de encontrar um livro numa divisão se já encontraste uma cadeira?
    print("Pergunta 7")
    pass


def resp8():
    # Se encontrares um enfermeiro numa divisão, qual é a probabilidade de estar lá um doente?
    print("Pergunta 8")
    pass
