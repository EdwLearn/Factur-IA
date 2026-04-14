#!/bin/bash
# Script para Testing Multi-Entorno con Docker
# Simula diferentes máquinas cliente conectándose al backend

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función de ayuda
show_help() {
    echo -e "${BLUE}=== FacturIA Multi-Environment Testing ===${NC}"
    echo ""
    echo "Uso: $0 [comando]"
    echo ""
    echo "Comandos disponibles:"
    echo "  start       - Inicia todos los contenedores de testing"
    echo "  stop        - Detiene todos los contenedores"
    echo "  restart     - Reinicia todos los contenedores"
    echo "  logs        - Muestra logs de todos los servicios"
    echo "  status      - Muestra el estado de los contenedores"
    echo "  test-client - Ejecuta tests desde un cliente específico"
    echo "  network     - Inspecciona la red de testing"
    echo "  clean       - Limpia todos los contenedores y volúmenes"
    echo "  help        - Muestra esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0 start"
    echo "  $0 logs test-client-windows"
    echo "  $0 test-client windows"
    echo ""
}

# Función para iniciar los contenedores
start_containers() {
    echo -e "${GREEN}🚀 Iniciando entorno de testing multi-máquina...${NC}"
    docker-compose -f docker-compose.multitest.yml up -d

    echo -e "${GREEN}✅ Contenedores iniciados${NC}"
    echo ""
    echo -e "${BLUE}Acceso a los clientes:${NC}"
    echo "  - Cliente Windows: http://localhost:3001"
    echo "  - Cliente Mac:     http://localhost:3002"
    echo "  - Cliente Linux:   http://localhost:3003"
    echo "  - Backend:         http://localhost:8001"
    echo ""
    echo -e "${YELLOW}Usa '$0 logs' para ver los logs${NC}"
}

# Función para detener los contenedores
stop_containers() {
    echo -e "${YELLOW}🛑 Deteniendo contenedores de testing...${NC}"
    docker-compose -f docker-compose.multitest.yml down
    echo -e "${GREEN}✅ Contenedores detenidos${NC}"
}

# Función para reiniciar los contenedores
restart_containers() {
    echo -e "${YELLOW}🔄 Reiniciando contenedores...${NC}"
    stop_containers
    start_containers
}

# Función para mostrar logs
show_logs() {
    if [ -z "$2" ]; then
        docker-compose -f docker-compose.multitest.yml logs -f
    else
        docker-compose -f docker-compose.multitest.yml logs -f "$2"
    fi
}

# Función para mostrar estado
show_status() {
    echo -e "${BLUE}📊 Estado de los contenedores:${NC}"
    docker-compose -f docker-compose.multitest.yml ps
    echo ""
    echo -e "${BLUE}🌐 Red de testing:${NC}"
    docker network inspect aws-document-processing_test-network --format '{{range .Containers}}{{.Name}}: {{.IPv4Address}}{{println}}{{end}}' 2>/dev/null || echo "Red no encontrada"
}

# Función para ejecutar tests desde un cliente
test_from_client() {
    if [ -z "$2" ]; then
        echo -e "${RED}❌ Debes especificar el cliente: windows, mac o linux${NC}"
        echo "Ejemplo: $0 test-client windows"
        exit 1
    fi

    CLIENT="test-client-$2"
    echo -e "${BLUE}🧪 Ejecutando tests desde cliente $2...${NC}"
    docker-compose -f docker-compose.multitest.yml exec "$CLIENT" npm test
}

# Función para inspeccionar la red
inspect_network() {
    echo -e "${BLUE}🔍 Inspeccionando red de testing...${NC}"
    echo ""
    echo -e "${GREEN}Contenedores en la red:${NC}"
    docker network inspect aws-document-processing_test-network --format '{{json .Containers}}' | jq -r 'to_entries[] | "\(.value.Name) - \(.value.IPv4Address)"'
    echo ""
    echo -e "${GREEN}Configuración de la red:${NC}"
    docker network inspect aws-document-processing_test-network --format '{{json .IPAM}}' | jq
}

# Función para limpiar todo
clean_all() {
    echo -e "${RED}🧹 Limpiando todos los contenedores y volúmenes...${NC}"
    read -p "¿Estás seguro? Esto eliminará todos los datos de testing (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose -f docker-compose.multitest.yml down -v
        echo -e "${GREEN}✅ Limpieza completada${NC}"
    else
        echo -e "${YELLOW}Operación cancelada${NC}"
    fi
}

# Función para verificar conectividad entre contenedores
check_connectivity() {
    echo -e "${BLUE}🔌 Verificando conectividad entre contenedores...${NC}"

    # Test desde cliente Windows al servidor
    echo -e "\n${YELLOW}Test: Windows -> Server${NC}"
    docker-compose -f docker-compose.multitest.yml exec test-client-windows \
        curl -s http://test-server:8000/health && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}"

    # Test desde cliente Mac al servidor
    echo -e "\n${YELLOW}Test: Mac -> Server${NC}"
    docker-compose -f docker-compose.multitest.yml exec test-client-mac \
        curl -s http://test-server:8000/health && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}"

    # Test desde cliente Linux al servidor
    echo -e "\n${YELLOW}Test: Linux -> Server${NC}"
    docker-compose -f docker-compose.multitest.yml exec test-client-linux \
        curl -s http://test-server:8000/health && echo -e "${GREEN}✓${NC}" || echo -e "${RED}✗${NC}"
}

# Main
case "$1" in
    start)
        start_containers
        ;;
    stop)
        stop_containers
        ;;
    restart)
        restart_containers
        ;;
    logs)
        show_logs "$@"
        ;;
    status)
        show_status
        ;;
    test-client)
        test_from_client "$@"
        ;;
    network)
        inspect_network
        ;;
    connectivity)
        check_connectivity
        ;;
    clean)
        clean_all
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        show_help
        exit 1
        ;;
esac
