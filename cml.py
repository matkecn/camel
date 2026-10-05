from src import CmlReader


cml = CmlReader("/Users/matkec/Desktop/projects/cml/config.cml")
configs = cml.read()

# for k, v in configs.items():
#     print("K={} V={}".format(k, v))

configs_extended = cml.fread()

# for k, v in configs_extended.items():
#     print("K={}, V={}".format(k, v))
print(configs_extended)
