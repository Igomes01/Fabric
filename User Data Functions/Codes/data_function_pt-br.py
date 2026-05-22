"""
AIC - Função de Dados do Usuário (FDU) para gerenciamento de ausências no Microsoft Fabric.

Este módulo implementa duas funções principais que se conectam a um Warehouse do Fabric
para inserir e deletar registros de ausência (Out of Office - OoO) de funcionários.

As funções são expostas como endpoints reutilizáveis via o framework fabric.functions,
podendo ser invocadas pelo Power BI ou por aplicativos externos.

Dependências:
    - fabric.functions: SDK do Fabric para criação de User Data Functions
    - re: Expressões regulares para parsing de IDs
    - time: Geração de timestamps para IDs únicos
    - random: Geração de bits aleatórios para IDs únicos
"""

import fabric.functions as fn
import re
import time
import random

# AIC - Inicializa o objeto principal do framework de Funções de Dados do Usuário.
# Este objeto é responsável por registrar e gerenciar todas as funções expostas.
udf = fn.UserDataFunctions()

# AIC - Nome do banco de dados (Warehouse) no Fabric.
# Deve ser preenchido com o nome exato do Warehouse criado na Etapa 1.
# Exemplo: warehouse_name = "MeuWarehouse"
warehouse_name = ""


def uuid_v7():
    """
    AIC - Gera um identificador único baseado em timestamp (inspirado no UUID v7).

    O ID é composto por:
        - 12 caracteres hexadecimais do timestamp em milissegundos (garante ordenação temporal)
        - 18 caracteres hexadecimais de bits aleatórios (garante unicidade)

    Retorna:
        str: ID único de 30 caracteres hexadecimais.

    Exemplo de retorno: "018f6b1a2c3d00a1b2c3d4e5f6a7b8"
    """
    # AIC - Captura o timestamp atual em milissegundos desde epoch (01/01/1970)
    timestamp_ms = int(time.time() * 1000)

    # AIC - Gera 74 bits aleatórios para compor a parte única do ID
    rand_bits = random.getrandbits(74)

    # AIC - Concatena timestamp (12 hex) + bits aleatórios (18 hex) formando o ID final
    return (
        f"{timestamp_ms:012x}"
        f"{rand_bits:018x}"
    )


@udf.connection(argName="myWarehouse", alias="MyWarehouse")
@udf.function()
def inserte_OoO(myWarehouse: fn.FabricSqlConnection, employee: str, ftype: str, startdate: str, enddate: str) -> str:
    """
    AIC - Insere um novo registro de ausência (OoO) na tabela fOoO do Warehouse.

    Esta função é invocada pelo botão "Save OoO" no Power BI.

    Decoradores:
        @udf.connection: Injeta a conexão com o Warehouse usando o alias "MyWarehouse"
                         configurado na etapa de Configurar Conexões da FDU.
        @udf.function: Registra esta função como um endpoint invocável.

    Parâmetros:
        myWarehouse (FabricSqlConnection): Conexão injetada automaticamente pelo Fabric.
        employee (str): Nome/identificador do funcionário (vem da medida "Connected User" no PBI).
        ftype (str): Tipo de ausência (ex: "Vacation", "OoO", "HHTO", "License").
        startdate (str): Data de início da ausência (formato: YYYY-MM-DD).
        enddate (str): Data de fim da ausência (formato: YYYY-MM-DD).

    Retorna:
        str: Mensagem de sucesso ("OoO Inserted") ou mensagem de erro.
    """

    # AIC - Gera um ID único para o novo registro de ausência
    id_gerado = uuid_v7()

    # AIC - Estabelece conexão com o Warehouse via o objeto injetado pelo decorator
    connection = myWarehouse.connect()
    cursor = connection.cursor()

    # AIC - Seleciona o banco de dados correto para execução das queries
    cursor.execute(f"USE [{warehouse_name}]")
    message = ""

    try:
        # AIC - Insere o registro na tabela fOoO usando parâmetros posicionais (?)
        # para prevenir SQL Injection
        query = f"INSERT INTO [{warehouse_name}].[dbo].[fOoO] (Id, Employee, Type, StartDate, EndDate) VALUES (?, ?, ?, ?, ?)"
        cursor.execute(query, id_gerado, employee, ftype, startdate, enddate)
        message = "OoO Inserted"
    except Exception as e:
        message = f"Erro ao processar: {e}"

    # AIC - Confirma a transação e libera os recursos de conexão
    connection.commit()
    cursor.close()
    connection.close()

    return message


@udf.connection(argName="myWarehouse", alias="MyWarehouse")
@udf.function()
def delete_OoO(myWarehouse: fn.FabricSqlConnection, employee: str, dateids: str) -> str:
    """
    AIC - Remove registros de ausência (OoO) da tabela fOoO do Warehouse.

    Esta função é invocada pelo botão "Remove OoO" no Power BI.
    Suporta a remoção de múltiplos registros de uma vez, recebendo os IDs
    em formato de string com aspas simples.

    Decoradores:
        @udf.connection: Injeta a conexão com o Warehouse usando o alias "MyWarehouse".
        @udf.function: Registra esta função como um endpoint invocável.

    Parâmetros:
        myWarehouse (FabricSqlConnection): Conexão injetada automaticamente pelo Fabric.
        employee (str): Nome/identificador do funcionário (vem da medida "Connected User" no PBI).
        dateids (str): String contendo IDs entre aspas simples para remoção.
                       Formato esperado: "'id1','id2','id3'"
                       (vem da medida "Delete Date" no PBI).

    Retorna:
        str: Mensagem de sucesso ("OoO Deleted") ou mensagem de erro do último item processado.
    """

    # AIC - Extrai todos os IDs da string usando regex.
    # O padrão r"'(.*?)'" captura o conteúdo entre aspas simples.
    # Exemplo: "'abc123','def456'" → ['abc123', 'def456']
    itens = re.findall(r"'(.*?)'", dateids)

    # AIC - Estabelece conexão com o Warehouse
    connection = myWarehouse.connect()
    cursor = connection.cursor()
    cursor.execute(f"USE [{warehouse_name}]")
    message = ""

    # AIC - Itera sobre cada ID para deletar individualmente
    for i in itens:
        try:
            # AIC - Deleta o registro usando Employee + Id como chave composta
            # para garantir que um usuário só delete seus próprios registros
            query = f"DELETE FROM [{warehouse_name}].[dbo].[fOoO] WHERE Employee = ? AND Id = ?"
            cursor.execute(query, employee, i)
            message = "OoO Deleted"
        except Exception as e:
            message = f"Erro ao processar: {e}"
            # AIC - Em caso de erro, pula para o próximo item sem interromper o loop
            continue

    # AIC - Confirma todas as deleções em uma única transação e libera recursos
    connection.commit()
    cursor.close()
    connection.close()

    return message