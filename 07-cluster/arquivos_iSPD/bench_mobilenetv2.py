# Mede o tempo por relato: decodificar foto JPEG 640x480, redimensionar para 224x224 e classificar com MobileNetV2 (1 thread de CPU)
import os, time, io, numpy as np
os.environ["TF_CPP_MIN_LOG_LEVEL"]="3"
import tensorflow as tf, keras
from keras import layers
from PIL import Image, ImageFilter
tf.config.threading.set_intra_op_parallelism_threads(1); tf.config.threading.set_inter_op_parallelism_threads(1)
base=keras.applications.MobileNetV2(input_shape=(224,224,3),include_top=False,weights=None)
inp=keras.Input((224,224,3)); x=layers.Rescaling(1/127.5,offset=-1)(inp); x=base(x,training=False); x=layers.GlobalAveragePooling2D()(x); x=layers.Dropout(0.3)(x); out=layers.Dense(1,activation="sigmoid")(x)
model=keras.Model(inp,out); print("parametros:",model.count_params())
f=tf.function(lambda t: model(t,training=False))
rng=np.random.default_rng(0)
# foto sintetica 640x480 (ruido suavizado), apenas para ter custo de decodificacao realista
im=Image.fromarray(rng.integers(0,255,(480,640,3),dtype=np.uint8)).filter(ImageFilter.GaussianBlur(2))
buf=io.BytesIO(); im.save(buf,"JPEG",quality=85); jpg=buf.getvalue(); print("JPEG sintetico (kB):",round(len(jpg)/1000,1))
def one():
    img=tf.image.resize(tf.io.decode_jpeg(jpg,channels=3),(224,224)); return f(img[None])
for _ in range(20): one()
ts=[]
for _ in range(300):
    t=time.perf_counter(); one(); ts.append(time.perf_counter()-t)
ts=np.array(ts)*1000
print("ms por relato: mediana",round(float(np.median(ts)),2),"| media",round(float(ts.mean()),2),"| p10",round(float(np.percentile(ts,10)),2),"| p90",round(float(np.percentile(ts,90)),2))
