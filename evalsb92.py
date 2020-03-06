#
# Usage: python evalsb92.py -i b91-corregida.mbz -o /tmp
#

import re
import xml.etree.ElementTree as ET
import collections as col
import gzip
import binascii
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.colors import ListedColormap
import os
import json
import sys
import getopt


import unicodedata


criteriosList = ['Asistencia', 'Puntualidad', 'Utilizacion Tiempo', 'Reposicion Ausencias', 'Horas de Oficina', 'Respetuoso', 'Dominio del Material', 'Cubre Temas', 'Presenta Organizado', 'Preparacion Para Clases', 'Claridad y Coherencia','Amplia Contenido Texto',  'Manifiesta Entusiasmo', 'Clase Interesante',  'Uso de Recursos',  'Estimula a Pensar', 'Fomenta Participacion',  'Ofrece Ayuda', 'Utiliza Ejemplos', 'Material Complementario', 'Anuncia con Tiempo', 'Examenes Sobre Material',  'Preguntas Claras',  'Tiempo Razonable Examen', 'Corrige a Tiempo', 'Justo Evaluando',  'Discute Examenes', 'Evaluacion Global']

# criteriosList = ['Entrega Prontuario', 'Presenta Objetivos', 'Asistencia', 'Puntualidad', 'Utilizacion Tiempo', 'Reposicion Ausencias', 'Horas de Oficina', 'Respetuoso', 'Dominio del Material', 'Cubre Temas', 'Presenta Organizado', 'Preparacion Para Clases', 'Claridad y Coherencia','Amplia Contenido Texto',  'Manifiesta Entusiasmo', 'Clase Interesante',  'Uso de Recursos',  'Estimula a Pensar', 'Fomenta Participacion',  'Ofrece Ayuda', 'Utiliza Ejemplos', 'Material Complementario', 'Anuncia con Tiempo', 'Examenes Sobre Material',  'Preguntas Claras',  'Tiempo Razonable Examen', 'Corrige a Tiempo', 'Justo Evaluando',  'Discute Examenes', 'Evaluacion Global', 'Recomienda Profesor', 'Aprovechamiento', 'Nota Parcial', 'Ano Estudio' ]




def strip_accents(s):
   return ''.join(c for c in unicodedata.normalize('NFD', s)
                  if unicodedata.category(c) != 'Mn')

def gz2Text(fileName):

    L = []
    mapita = {}
    for i in range(128,256):
        L.append(bytes([i]))
        mapita[i] = ''

    with gzip.open(fileName, 'rb') as f:
        fileContents = f.read()

    # Soy un vago y no quiero buscar como hacer esto ...
    mapita[168] = 'a'
    mapita[170] = 'u'
    mapita[171] = 'i'
    mapita[171] = 'i'
    mapita[172] = 'i'
    mapita[173] = 'i'
    mapita[174] = 'i'
    mapita[175] = 'i'
    mapita[176] = 'i'
     
    mapita[169] = 'e'
    mapita[179] = 'o'
    mapita[177] = 'n'

    # print(type(fileContents[0]))
    # esto es un marron para que funcione en las macs.
    if type(fileContents[0]) is int:
        fileContents = ''.join([chr(i) if i < 195 else '' for i in fileContents])
        fileContents = ''.join([i if ord(i) < 128  else mapita[ord(i)] for i in fileContents])
        return fileContents


    fileContents = ''.join([i if ord(i) < 195 else '' for i in fileContents])
    fileContents = ''.join([i if ord(i) < 128  else mapita[ord(i)] for i in fileContents])
    return fileContents.decode()

# Dado el nombre del file, convierte de XML a json la info que nos interesa

def extractJSON(fileName):
    print("Extracting JSON......")
    
    fileContents = gz2Text(fileName)
    regex = r"(?:<activity id[\S\s]*?[\S\s]*?<\/activity>)"

    # print(fileContents)

    matches = re.finditer(regex, fileContents, re.MULTILINE)

    L = []
    for matchNum, match in enumerate(matches):
        matchNum = matchNum + 1
        L.append( match.group())   


    Todos = {}
    ctr = 1
    
    for act in L[:]:
        M = {}
        root = ET.fromstring(act)
        print(ctr, "NAME:" , root.find('feedback').findtext('name')) #root = tree.getroot()
        for child in root.find('feedback').find('items'):
            options = child.findtext('presentation').replace("\n", "").replace("r>>>>>", "").replace("<<<<<1", "").split("|")
            M[child.attrib['id']] = {'label' : child.findtext('label'), 'options': options, 'values':[]}

        
        for child in root.find('feedback').find('completeds'):
            for v in child.find('values'):
                M[v.findtext('item')]['values'].append(v.findtext('value'))
        Todos[root.find('feedback').findtext('name')] = M
        ctr = ctr + 1
    return Todos 

# Returns the weighted sum and the total non N/A

def weightedSum(ctr, w):
    i = 0
    ws = 0
    for wi in w:
        ws = ws + ctr[str(i+1)]*w[i]
        i = i + 1

    count = ctr['1'] + ctr['2'] + ctr['3'] + ctr['4'] 
    return ws, count

def calcStats(record):
    for key in record:
        ctr = col.Counter(record[key]['values'])
        if len(record[key]['options']) == 5:
            tmp = [record[key]['options'][int(i)-1] for i in record[key]['values']]
            record[key]['sum'],record[key]['ctr'] =  weightedSum(ctr,[4,3,2,1])
            ctrWithNames = col.Counter(tmp)
            record[key]['hist'] = ctrWithNames
        elif len(record[key]['options']) == 2 and record[key]['options'][0] == 'Si':
            tmp = [record[key]['options'][int(i)-1] for i in record[key]['values']]
            record[key]['sum'],record[key]['ctr'] =  weightedSum(ctr,[4,0])
            ctrWithNames = col.Counter(tmp)
            record[key]['hist'] = ctrWithNames


def pandaPlot(section, allJSON, outputDir):
    test = allJSON[section]


    testKeys = [k for k in test]
    
    clasif = ['Excelente', 'Bueno', 'Regular', 'Deficiente', 'No Aplica']

    tmpDict = {}

    for kk in clasif:
        tmpDict[kk] = {}    
    
    questionList= []
    for key in test: 
        if (test[key]['options'][0] == 'Excelente'):
            for kk in dict(test[key]['hist']):
                tmpDict[kk][test[key]['label']] = test[key]['hist'][kk]
            questionList.append(test[key]['label'])

    # print("questionList", questionList)

    dic = tmpDict
    df = pd.DataFrame(dic)

    orderClasses =['Excelente', 'Bueno', 'Regular', 'Deficiente', 'No Aplica'] 

    indexList = [i for i in df.index]



    questionOrder = [indexList.index(i) for i in criteriosList] # questionsList



    f = df.iloc[questionOrder,[2,0,4,1,3]].plot(kind="bar", stacked=True, figsize = (14,5), title=section)
    f = f.get_figure()
    f.savefig( outputDir + '/' + section + '.pdf', pad_inches=1,bbox_inches="tight")
    



def saveComments(section, allJSON, outputDir):     
    testTmp = allJSON[section]
    comments = [testTmp[key]['values'] for key in testTmp if testTmp[key]['label'] == 'Comentarios' ]
    comments = [i for i in comments[0] if len(i) > 0 ]
    f = open("%s/%s-Comentarios.txt" % (outputDir, section), "w")
    f.write("Comentarios para %s\n\n" % section)
    f.write("==============================================================\n\n" )
    for c in comments:
        # correct = replaceInternational(c)
        f.write("* %s\n\n" % c)

def computeAvg(allJSON):
    avgsDict = {}
    resultDict = {}
    ctr = 0
    for k in allJSON:
        val = allJSON[k]
        if ctr == 0:
            for q in val:
                if 'sum' in val[q]:
                    avgsDict[val[q]['label']] = []
        
        for q in val:
            if 'sum' in val[q] and val[q]['sum'] != 0:
                avgsDict[val[q]['label']].append(float(val[q]['sum'])/float(val[q]['ctr']))
        ctr = ctr + 1
    
    for k in avgsDict:
        resultDict[k] = sum(avgsDict[k]) / float(len(avgsDict[k]))
    return resultDict


def plotAgainstAvg(section, allJSON, allAvgs, outputDir):
    print(section)
    tmpNow = allJSON[section]
    tmpForPandas = {}
    tmpForPandas[section] = []
    tmpForPandas['Promedio CCOM'] = []
    tmpQuestions = []

    criterios10 = ['Preparacion Para Clases','Dominio del Material', 'Claridad y Coherencia', 'Manifiesta Entusiasmo', 'Presenta Organizado', 'Estimula a Pensar', 'Ofrece Ayuda', 'Examenes Sobre Material', 'Justo Evaluando', 'Fomenta Participacion']

    criteriosSum = 0

    print("===================================================")
        
    for k in tmpNow:
        val = tmpNow[k]
        if 'sum' in val and int(val['ctr']) != 0:
            if val['label'] in criterios10:
                print("%s\t%f\tEstudiantes: %s" %(val['label'].ljust(25),round(float(val['sum'])/float(val['ctr']),3), val['ctr']  ))
                criteriosSum = criteriosSum + float(val['sum'])/float(val['ctr'])
            
            if val['label'] in criteriosList:
                tmpForPandas[section].append( float(val['sum'])/float(val['ctr']))
                tmpForPandas['Promedio CCOM'].append(allAvgs[val['label']])
                tmpQuestions.append(val['label'])
            # else:
            #     print("Criterium [%s] not found" % val['label'])

    print("===================================================")
    print("Promedio de 10 criterios:\t%f" % round(criteriosSum / 10.0,3))
    print("")


    # Esto es un marron por si ningun estudiante contesto cierta pregunta
    diff = set(criteriosList).difference(set(tmpQuestions))
    tmpList = [i for i in criteriosList]
    if len(diff) != 0:
        for e in diff:
            tmpList.remove(e)
   
    questionOrder = [tmpQuestions.index(i) for i in tmpList]
    
    pa = pd.DataFrame(tmpForPandas, index=tmpQuestions)  #tmpList

    f = pa.iloc[questionOrder].plot(kind="bar",figsize = (11,5), title=section, alpha=0.55)
    plt.legend(loc='lower left',framealpha = 1)
    f = f.get_figure()
    f.savefig( outputDir + '/' + section + 'vsAll.pdf', pad_inches=1,bbox_inches="tight")


def main(argv, execName):
    filename = ''
    outputDir = ''

    try:
        opts, args = getopt.getopt(argv,"hi:o:",["ifile=","ofile="])

    except getopt.GetoptError:
        print("%s -i <inputfile> -o <outputfile>" % execName)
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print("%s -i <inputfile> -o <outputfile>" % execName)
            sys.exit()
        elif opt in ("-i", "--ifile"):
            filename = arg
        elif opt in ("-o", "--ofile"):
            outputDir = arg

    if len(argv) < 2:
        print("%s -i <inputfile> -o <outputfile>" % execName)
        sys.exit()     

    print("Input file: %s" % filename)
    print("Output dir: %s" % outputDir)

    
    allJSON = extractJSON(filename)

    for k in allJSON:
        calcStats(allJSON[k])

    for k in allJSON:
        print (k)
        pandaPlot(k,allJSON, outputDir)

    allAvgs = computeAvg(allJSON)
    for k in allJSON:
        plotAgainstAvg(k, allJSON, allAvgs, outputDir)

    for key in allJSON:
        saveComments(key, allJSON, outputDir)




if __name__ == "__main__":
   main(sys.argv[1:], sys.argv[0])

