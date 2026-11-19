# Resultados calculados

### Teste com áudios inéditos (Model testing)

Acertos: **14 de 15** (93.3 %)

| Classe | Acertos | Tentativas | Percentual |
| --- | --- | --- | --- |
| ambiente_rua | 4 | 5 | 80.0 % |
| buzina | 5 | 5 | 100.0 % |
| sirene | 5 | 5 | 100.0 % |
| **Total** | **14** | **15** | **93.3 %** |

Matriz de confusão (quantidade):

| | Previsto: ambiente_rua | Previsto: buzina | Previsto: sirene | Previsto: uncertain |
| --- | --- | --- | --- | --- |
| **Real: ambiente_rua** | 4 | 0 | 1 | 0 |
| **Real: buzina** | 0 | 5 | 0 | 0 |
| **Real: sirene** | 0 | 0 | 5 | 0 |

Falsos positivos em ambiente_rua: **1 de 5** (1x sirene)
Imagem da matriz: img/matriz_teste_arquivos.png
