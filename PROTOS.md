Protobufs / How to handle `fabric-protos`
========================================

Resumen
-------

Hyperledger Fabric define sus interfaces gRPC en `fabric-protos` (Apache-2.0). Para implementar un shim en Python hay dos opciones razonables:

1. "Submodular / generar": Mantener `fabric-protos` como submódulo (o referenciar una versión fija), y generar los archivos Python (`*_pb2.py`, `*_pb2_grpc.py`) con `grpc_tools.protoc` usando `scripts/gen_protos.sh`. Opcionalmente, incluir los archivos generados en `src/protos/` para simplificar la instalación de usuarios.

2. "Empaquetar protos pre-generados": Incluir directamente los archivos Python generados en el paquete (`src/`), y documentar la versión de `fabric-protos` usada. Esto evita que los consumidores instalen `grpc_tools` para usar la librería.

Recomendación (mejor equilibrio al comenzar)
------------------------------------------

- Use `fabric-protos` como submódulo apuntando a la versión que quiere soportar (por ejemplo `v2.4.0`). Esto preserva el historial y permite reproducibilidad.
- Añada `scripts/gen_protos.sh` (ya existe) para generar bindings. Committee los archivos generados en `src/protos/` solo para releases (o para facilitar pruebas), pero mantenga la fuente `.proto` separada.
- En `pyproject.toml` incluya los archivos generados en el paquete (o genere en la fase de `bdist_wheel`). En CI, genere y valide que los archivos generados son consistentes con el submódulo.
- No publique un paquete PyPI con el nombre `fabric-protos-python` que pueda confundirse con proyectos oficiales; si usted ya tiene un paquete con ese nombre, prefiera un nombre con un prefijo (por ejemplo `fabric_protos_py` o `hyperledger_fabric_protos_py`) y documente claramente la compatibilidad de versión.

Pasos prácticos (ejemplo)
-------------------------

1. Añadir `fabric-protos` como submódulo:

```bash
git submodule add --depth 1 -b v2.4.0 https://github.com/hyperledger/fabric-protos.git protos/fabric-protos
git submodule update --init --recursive
```

2. Generar los protos Python (desde la raíz del repo):

```bash
cd ./fabric-chaincode-python
./scripts/gen_protos.sh
# los archivos generados irán a src/protos/ por defecto
```

3. Validar en CI que los protos generados son consistentes o regenerarlos en la fase de build.

Licencia
--------

`fabric-protos` está bajo Apache-2.0. Si incluye `.proto` o archivos generados en su repo, conserve la referencia de licencia (no elimine los archivos LICENSE de `fabric-protos` si los copia). Esto es necesario para poder migrar a Hyperledger Labs sin problemas.
