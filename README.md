[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=pabloosp_VehicleDetection&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=pabloosp_VehicleDetection)

# Vehicle Detection

VehicleDetection es una aplicación web desarrollada como Trabajo de Fin de Grado en Ingeniería Informática por la Universidad de Burgos. Su objetivo es controlar el acceso de vehículos a las distintas facultades de la universidad mediante el análisis automático de vídeos usando técnicas de visión por computador y aprendizaje profundo.

La aplicación cuenta con dos tipos de usuarios:

- **Experto**: permite al usuario seleccionar varias opciones y subir un vídeo.  
  El sistema detecta automáticamente a qué facultad corresponde el vídeo y contabiliza los vehículos que acceden.  
  Los registros de vehículos detectados se almacenan en la base de datos.

- **Usuario**: puede visualizar los resultados de un periodo seleccionado mediante tablas, estadísticas y gráficos interactivos.


## Instalación en local

Es necesaria la instalación de los siguientes componentes

- **Python** 3.11.1
- **MySQL Installer** 8.0.42
  - *MySQL Server*
  - *MySQL Workbench*
- **Librerías de Python**
  - **Flask** 
  - **Torch** 2.5.1+cu121
  - **Ultralytics** 
  - **OpenCV** 
  - **PyMediaInfo** 
  - **Shapely** 
  - **python-dotenv**
  - **mysql-connector-python**

Además:

- Es necesario conceder permisos adecuados al usuario de **MySQL** para permitir la conexión con la app.
- Renombrar el archivo .env.example a .env y completar las variables necesarias.


### Pasos

Instalar las librerías de Python:

```bash
$ pip install -r requirements.txt
```

Lanzar la aplicación

```bash
$ cd src
$ py app.py
```

Esto levantará la aplicación en http://localhost:5000

La aplicación se encuentra disponible en los siguientes idiomas:
- Español
- Inglés

## Licencia

Este proyecto está licenciado bajo la **GNU Affero General Public License v3.0 (AGPL-3.0)**.  
Consulta el archivo [LICENSE](./LICENSE) para más detalles.

---

---

# Vehicle Detection

**VehicleDetection** is a web application developed as a Bachelor’s Thesis in Computer Science at the University of Burgos.  
Its goal is to monitor vehicle access to the different faculties of the university through the automatic analysis of videos using computer vision and deep learning techniques.

The application features two types of users:

- **Expert**: allows the user to select various options and upload a video.  
  The system automatically detects which faculty the video corresponds to and counts the vehicles entering.  
  Detected vehicle records are stored in the database.

- **User**: can view the results for a selected period through tables, statistics, and interactive charts.

## Local Installation

The following components must be installed:

- **Python** 3.11.1
- **MySQL Installer** 8.0.42  
  - *MySQL Server*  
  - *MySQL Workbench*
- **Python Libraries**
  - **Flask**
  - **Torch** 2.5.1+cu121
  - **Ultralytics**
  - **OpenCV**
  - **PyMediaInfo**
  - **Shapely**
  - **python-dotenv**
  - **mysql-connector-python**

Additionally:

- The **MySQL** user must have the appropriate permissions to allow the app to connect.
- Rename the `.env.example` file to `.env` and fill in the required variables.

### Steps

Install the required Python libraries:


```bash
$ pip install -r requirements.txt
```

Run the app

```bash
$ cd src
$ py app.py
```
This will start the application at http://localhost:5000

The application is available in the following languages:
- Spanish
- English

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**.  
See the [LICENSE](./LICENSE) file for more details.

