#!/bin/bash
#845097, Valle Morenilla, Juan, T, 1, A
#839757, Ye, Ming Tao, T, 1, A

# Comprobamos que el usuario tiene privilegios de administrador
if [ "$EUID" != 0 ]; then
    echo "Este script necesita privilegios de administracion"
    exit 1
fi

# Comprobamos si el número de parámetros es el correcto (2)
if [ "$#" != 2 ]; then
    echo "Numero incorrecto de parametros">&2
    exit 1
fi

# Comprobamos que los parámetros introducidos son correctos
if [[ "$1" != -a] && ["$1" != -s ]]; then
    echo "Opcion invalida" >&2
    exit 1
fi

# Añadimos usuarios
if [ "$1" == "-a" ]; then
    id=1815
    while IFS=',' read nombre contrasena nombreCompleto
    do
        # Comprobamos que los campos no son la cadena vacía
        if [[ -z "$nombre" | -z "$contrasena" | -z "$nombreCompleto" ]]; then
            echo "Campo invalido"
            exit 1
        fi
        # Comprobamos que el usuario existe
        if [ ! (grep -q "^$nombre" /etc/passwd) ]; then     # grep -q = 0 si hay matches
            # -u: UID   ;   -U: crea grupo llamado como el usuario y lo añade
            # -m: crea HOME copiando ficheros del etc/skel
            # -c: comentarios
            useradd -u "$id" -U -m -c "$nombreCompleto" "$nombre"
            sudo chage -M 30 "$nombre"      # Contraseña válida 30 días para usuario
            echo "$nombreCompleto ha sido creado."
            ((id++))
        else
            echo "El usuario $id ya existe."
        fi
    done < "$1"   # La stdIn del bucle es el fichero pasado por parámetro

# Borramos usuarios
else
    if [ ! -d /extra/backup ]; then   # Creamos el directorio backup si no existe
         mkdir -p /extra/backup
    fi
    while IFS=',' read nombre contrasena nombreCompleto
    do
        if [ -z "$nombre"]; then    # Comprueba que no sea la cadena vacía
            echo "Campo invalido"
            exit 1
        fi
        # Comprueba que exista el usuario
        if [ ! (grep -q "^$nombre" /etc/passwd) ]; then     # grep -q = 0 si hay matches
            # Obtenemos el directorio home a partir de la info de etc/passwd
            # que tiene el usuario en su 6º campo
            home=$(grep "$nombre" /etc/passwd | cut -d: -f6)          
            tar czpf /extra/backup/"$nombre".tar "$home"
            
            # Borramos usuario si el backup ha ido bien
            if [ ! "$?" ]; then
                userdel -r "$nombre"
            fi
        fi
    done < "$1"   # La stdIn del bucle es el fichero pasado por parámetro
fi
