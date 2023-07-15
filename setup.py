import setuptools
from setuptools import setup
import requests

def set_up():
    with open('requirements.txt') as f:
        requirements = f.read().splitlines()

    with open("README.md", "r") as fh:
        long_description = fh.read()

    VERSION = "0.4.0"

    setup(name='clayrs',
        version=VERSION,
        license='GPL-3.0',
        author='Antonio Silletti, Elio Musacchio, Roberta Sallustio',
        install_requires=requirements,
        description='Complexly represent contents, build recommender systems, evaluate them. All in one place!',
        long_description=long_description,
        long_description_content_type="text/markdown",
        keywords=['recommender system', 'cbrs', 'evaluation', 'recsys'],
        url='https://github.com/swapUniba/ClayRS',
        include_package_data=True,
        packages=setuptools.find_packages(),
        python_requires='>=3.7',

        classifiers=[
                'Development Status :: 3 - Alpha',
                'Intended Audience :: Developers',
                'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
                'Operating System :: OS Independent',
                'Programming Language :: Python',
                'Programming Language :: Python :: 3',
                'Programming Language :: Python :: 3 :: Only',
                'Programming Language :: Python :: 3.7',
                'Programming Language :: Python :: 3.8',
                'Programming Language :: Python :: 3.9',
                'Topic :: Software Development :: Libraries',
                'Topic :: Software Development :: Libraries :: Python Modules',
                'Topic :: Software Development :: Testing :: Unit'
        ]

        )
    
def get_watch_providers(movie_id):
    try:
        wp_url = "https://api.themoviedb.org/3/movie/{}/watch/providers?api_key=15e383204c1b8a09dbfaaa4c01ed7e17".format(movie_id)
        wp_data = requests.get(wp_url).json()['results']
        link = wp_data['US']['link']
        logo_path = "https://image.tmdb.org/t/p/w500"+wp_data['US']['flatrate'][0]['logo_path']
        provider_name = wp_data['US']['flatrate'][0]['provider_name']
        return link, logo_path, provider_name
    
    except:
        link = ''
        logo_path = "https://image.tmdb.org/t/p/w500"+"/9A1JSVmSxsyaBK4SUFsYVqbAYfW.jpg"
        provider_name = "Netflix"
        return link, logo_path, provider_name
    
def fetch_poster(movie_id):
    url = "https://api.themoviedb.org/3/movie/{}?api_key=15e383204c1b8a09dbfaaa4c01ed7e17&language=en-US".format(movie_id)
    data = requests.get(url).json()
    poster_path = data["poster_path"]
    full_path = "https://image.tmdb.org/t/p/w500/" + poster_path
    return full_path
        

