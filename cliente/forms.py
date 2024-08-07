from django import forms
from .models import cadastro_de_cliente, LISTA_ESTADOS, LISTA_RAMOS

class Cadastrodeclientes(forms.ModelForm):

    class Meta:
        model = cadastro_de_cliente
        fields = "__all__"
        widgets = {'razao_social': forms.TextInput(attrs={'class': 'form-control'}),
                  'cnpj': forms.NumberInput(attrs={'class': 'form-control'}),
                  'logadouro': forms.TextInput(attrs={'class': 'form-control'}),
                  'bairro': forms.TextInput(attrs={'class': 'form-control'}),
                  'número': forms.NumberInput(attrs={'class': 'form-control'}),
                  'cidade': forms.TextInput(attrs={'class': 'form-control'}),
                  'estado': forms.Select(choices=LISTA_ESTADOS, attrs={'class': 'form-control'}),
                  'pessoa_de_contato': forms.TextInput(attrs={'class': 'form-control'}),
                  'telefone': forms.NumberInput(attrs={'class': 'form-control'}),
                  'email_contato': forms.EmailInput(attrs={'class': 'form-control'}),
                  'ramo': forms.Select(choices=LISTA_RAMOS, attrs={'class': 'form-control'}),
                  'bancos_utilizados': forms.TextInput(attrs={'class': 'form-control'}),
                  'servicos_contratados': forms.TextInput(attrs={'class': 'form-control'}),
                  'responsavel_conciliacao': forms.TextInput(attrs={'class': 'form-control'}),
                  'responsavel_apresentacao': forms.TextInput(attrs={'class': 'form-control'}),
                  'funcionarios': forms.Textarea(attrs={'class': 'form-control'}),
                  'contas_fixas': forms.Textarea(attrs={'class': 'form-control'}),
                  'classificacoes': forms.Textarea(attrs={'class': 'form-control'}),
                  'principais_fornecedores': forms.Textarea(attrs={'class': 'form-control'}),
                  'observacoes': forms.Textarea(attrs={'class': 'form-control'}),
                  'sugestoes': forms.Textarea(attrs={'class': 'form-control'}),
                  'historico': forms.Textarea(attrs={'class': 'form-control'}),
        }